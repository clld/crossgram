from __future__ import unicode_literals

from collections import OrderedDict
import pathlib
import re
import sys

from datetime import date

import cldfcatalog
from clld.cliutil import Data
from clld.db.meta import DBSession
from clld.db.models import common
from clldutils import jsonlib
from clldutils.misc import slug
from pyglottolog import Glottolog

import git
from markdown import markdown

import crossgram
from crossgram import models
from crossgram.lib.cldf import CLDFBenchSubmission
from crossgram.lib.cldf_zenodo import download_from_doi


def main(args):
    internal = input('[i]nternal or [e]xternal data (default: e): ').strip().lower() == 'i'
    which_submission = input("submission id or 'all' for all submissions (default: all): ").strip().lower() or 'all'

    data = Data()

    dataset = common.Dataset(
        id=crossgram.__name__,
        name='Crossgram',
        published=date(2019, 12, 12),
        domain='crossgram.clld.org',
        # XXX Is any of this correct?
        publisher_name='Max Planck Institute for the Science of Human History',
        publisher_place='Jena',
        publisher_url='https://ssh.mpg.de',
        license='http://creativecommons.org/licenses/by/4.0',
        jsondata={
            'license_icon': 'cc-by.png',
            'license_name': 'Creative Commons Attribution 4.0 International License'})

    for i, (id_, name) in enumerate([
        ('haspelmathmartin', 'Martin Haspelmath'),
    ]):
        ed = data.add(common.Contributor, id_, id=id_, name=name)
        common.Editor(dataset=dataset, contributor=ed, ord=i + 1)
    DBSession.add(dataset)

    internal_repo = pathlib.Path('../../crossgram/crossgram-internal')
    cache_dir = internal_repo / 'datasets'
    cache_dir.mkdir(exist_ok=True)

    if internal:
        submissions_path = internal_repo / 'submissions-internal'
    else:
        submissions_path = internal_repo / 'submissions'

    language_id_map = {}
    for contrib_dir in submissions_path.iterdir():
        if not contrib_dir.is_dir():
            continue
        if which_submission != 'all' and which_submission != contrib_dir.name:
            continue
        sid = contrib_dir.name
        print('Loading submission', sid, '...')

        contrib_md = jsonlib.load(contrib_dir / 'md.json')
        intro = None
        try:
            with (contrib_dir / 'intro.md').open(encoding='utf-8') as f:
                intro = f.read()
        except IOError:
            # If there is no intro, there is no intro *shrug*
            pass

        if contrib_md.get('doi'):
            doi = contrib_md['doi']
            path = cache_dir / '{}-{}'.format(sid, slug(doi))
            if not path.exists():
                print('Downloading dataset from Zenodo; doi:', doi)
                download_from_doi(doi, path)

        elif contrib_md.get('repo'):
            repo = contrib_md.get('repo')
            checkout = contrib_md.get('checkout')
            if checkout:
                # specific commit/tag/branch
                path = cache_dir / '{}-{}'.format(sid, slug(checkout))
                if not path.exists():
                    print('Cloning', repo, 'into', path, '...')
                    git.Git().clone(repo, path)
                    print('Checking out commit', checkout, '...')
                    git.Git(str(path)).checkout(checkout)
            else:
                # latest commit on the default branch
                path = cache_dir / sid
                if not path.exists():
                    print('Cloning', repo, 'into', path, '...')
                    git.Git().clone(repo, path)
                else:
                    print('Pulling latest commit')
                    git.Git(str(path)).pull()

        else:
            path = cache_dir / sid

        if not path.exists():
            print('could not find folder', str(path))
            continue

        submission = CLDFBenchSubmission.load(path, contrib_md)

        date_match = re.fullmatch('(\d+)-(\d+)-(\d+)', contrib_md['published'])
        assert date_match
        yyyy, mm, dd = date_match.groups()
        published = date(int(yyyy), int(mm), int(dd))

        contrib = data.add(
            models.CrossgramData,
            submission.sid,
            id=submission.sid,
            number=int(contrib_md['number']),
            published=published,
            name=submission.title,
            description=intro or submission.readme)

        submission.add_to_database(data, language_id_map, contrib)
        print('... done')


def prime_cache(args):
    """If data needs to be denormalized for lookup, do that here.
    This procedure should be separate from the db initialization, because
    it will have to be run periodically whenever data has been updated.
    """

    print('Parsing markdown intros...')
    for contrib in DBSession.query(models.Contribution):
        if contrib.description:
            contrib.markup_description = markdown(contrib.description)
        else:
            contrib.markup_description = None
    print('...done')

    print('Retrieving language data from glottolog...')

    catconf = cldfcatalog.Config.from_file()
    glottolog_path = catconf.get_clone('glottolog')
    glottolog = Glottolog(glottolog_path)

    lang_ids = [lang.id for lang in DBSession.query(common.Language)]
    languoids = {l.id: l for l in glottolog.languoids(lang_ids)}

    glottocodes = [
        (l.id, common.Identifier(id=l.id, name=l.id, type='glottolog'))
        for l in languoids.values()]
    glottocodes = OrderedDict(sorted(glottocodes, key=lambda t: t[0]))

    isocodes = [
        (l.iso, common.Identifier(id=l.iso, name=l.iso, type='iso639-3'))
        for l in languoids.values()
        if l.iso]
    isocodes = OrderedDict(sorted(isocodes, key=lambda t: t[0]))

    DBSession.add_all(glottocodes.values())
    DBSession.add_all(isocodes.values())
    DBSession.flush()

    for lang in DBSession.query(common.Language):
        if lang.id not in languoids:
            continue
        languoid = languoids[lang.id]
        lang.name = languoid.name
        lang.latitude = languoid.latitude
        lang.longitude = languoid.longitude
        lang.macroarea = languoid.macroareas[0].name if languoid.macroareas else ''

        DBSession.add(common.LanguageIdentifier(
            language=lang,
            identifier_pk=glottocodes[languoid.id].pk))

        if languoid.iso in isocodes:
            DBSession.add(common.LanguageIdentifier(
                language=lang,
                identifier_pk=isocodes[languoid.iso].pk))

    DBSession.flush()
    print('done...')
