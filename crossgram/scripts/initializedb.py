from __future__ import unicode_literals

from collections import OrderedDict
from itertools import cycle, groupby
import pathlib
import re

from datetime import date

import cldfcatalog
from clld.cliutil import Data
from clld.db.meta import DBSession
from clld.db.models import common
from clld.web.icon import ORDERED_ICONS
from clldutils import jsonlib
from clldutils.misc import slug
from clld_glottologfamily_plugin.util import load_families
from pyglottolog import Glottolog

import git
from markdown import markdown
import sqlalchemy

import crossgram
from crossgram import models
from crossgram.lib.cldf import CLDFBenchSubmission
from crossgram.lib.cldf_zenodo import download_from_doi


def download_data(sid, contrib_md, cache_dir):
    if contrib_md.get('doi'):
        doi = contrib_md['doi']
        path = cache_dir / '{}-{}'.format(sid, slug(doi))
        if not path.exists():
            print(' * downloading dataset from Zenodo; doi:', doi)
            download_from_doi(doi, path)
            print('   done.')
        return path

    elif contrib_md.get('repo'):
        repo = contrib_md.get('repo')
        checkout = contrib_md.get('checkout')
        if checkout:
            # specific commit/tag/branch
            path = cache_dir / '{}-{}'.format(sid, slug(checkout))
            if not path.exists():
                print(' * cloning', repo, 'into', path, '...')
                git.Git().clone(repo, path)
                print('   done.')
                print(' * checking out commit', checkout, '...')
                git.Git(str(path)).checkout(checkout)
                print('   done.')
        else:
            # latest commit on the default branch
            path = cache_dir / sid
            if not path.exists():
                print(' * cloning', repo, 'into', path, '...')
                git.Git().clone(repo, path)
                print('   done.')
            else:
                print(' * pulling latest commit')
                git.Git(str(path)).pull()
                print('   done.')
        return path

    else:
        return cache_dir / sid


def collect_language_sources():
    existing_sources = set(DBSession.execute(
        sqlalchemy.select(
            models.LanguageReference.language_pk,
            models.LanguageReference.source_pk)
        .distinct()))

    language_sources = set(DBSession.execute(
        sqlalchemy.select(
            common.ValueSet.language_pk,
            common.ValueSetReference.source_pk)
        .join(common.ValueSetReference.valueset)
        .distinct()))
    language_sources.update(DBSession.execute(
        sqlalchemy.select(
            common.Unit.language_pk,
            models.UnitValueReference.source_pk)
        .join(models.UnitValueReference.unitvalue)
        .join(common.UnitValue.unit)
        .distinct()))
    language_sources.update(DBSession.execute(
        sqlalchemy.select(
            common.Unit.language_pk,
            models.UnitReference.source_pk)
        .join(models.UnitReference.unit)
        .distinct()))
    language_sources = sorted(language_sources - existing_sources)

    DBSession.add_all(
        models.LanguageReference(
            language_pk=language_pk,
            source_pk=source_pk)
        for language_pk, source_pk in language_sources)


def main(args):
    internal = input('[i]nternal or [e]xternal data (default: e): ').strip().lower() == 'i'
    which_submission = input("submission id or 'all' for all submissions (default: all): ").strip().lower() or 'all'

    data = Data()

    dataset = common.Dataset(
        id=crossgram.__name__,
        name='Crossgram',
        description='Crossgram',
        published=date(2019, 12, 12),
        domain='crossgram.clld.org',
        publisher_name='Max Planck Institute for Evolutionary Anthropology',
        publisher_place='Leipzig',
        publisher_url='https://www.eva.mpg.de',
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

    for contrib_dir in submissions_path.iterdir():
        if not contrib_dir.is_dir():
            continue
        if which_submission != 'all' and which_submission != contrib_dir.name:
            continue
        sid = contrib_dir.name
        print('Loading submission', sid, '...')

        contrib_md = jsonlib.load(contrib_dir / 'md.json')
        if contrib_md.get('hide'):
            print('... but', sid, "doesn't want to be shown")
            continue
        intro = None
        try:
            with (contrib_dir / 'intro.md').open(encoding='utf-8') as f:
                intro = f.read()
        except IOError:
            # If there is no intro, there is no intro *shrug*
            pass

        path = download_data(sid, contrib_md, cache_dir)
        if not path.exists():
            print('could not find folder', str(path))
            continue

        submission = CLDFBenchSubmission.load(path, contrib_md)

        date_match = re.fullmatch(r'(\d+)-(\d+)-(\d+)', contrib_md['published'])
        assert date_match
        yyyy, mm, dd = date_match.groups()
        published = date(int(yyyy), int(mm), int(dd))

        # strip off ssh stuff off git link
        git_https = re.sub(
            '^git@([^:]*):', r'https://\1/', contrib_md.get('repo') or '')

        contrib = data.add(
            models.CrossgramData,
            sid,
            id=sid,
            number=int(contrib_md['number']),
            published=published,
            name=contrib_md.get('title') or submission.title,
            doi=contrib_md.get('doi'),
            git_repo=git_https,
            description=intro or submission.readme)

        submission.add_to_database(data, contrib)
        print('... done')

    DBSession.flush()
    print('Loading language family data...')
    catconf = cldfcatalog.Config.from_file()
    glottolog_path = catconf.get_clone('glottolog')
    load_families(
        Data(),
        [
            v for v in DBSession.query(models.Variety)
            if re.fullmatch('[a-z]{4}[0-9]{4}', v.id)
        ],
        strict=False,
        glottolog_repos=glottolog_path)
    print('... done')

    print('Collecting language sources...')
    collect_language_sources()
    DBSession.flush()
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
    print('... done')

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
        lang.glottolog_id = languoid.id
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
    print('... done')

    print('Counting things...')

    # language representation for l-parameters
    DBSession.execute(sqlalchemy.text("""
        UPDATE lparameter
        SET language_count = s.c
        FROM (
            SELECT parameter_pk, count(distinct(language_pk)) AS c
            FROM valueset
            GROUP BY parameter_pk
        ) AS s
        WHERE lparameter.pk = s.parameter_pk
    """))

    # language representation for l-parameter codes
    DBSession.execute(sqlalchemy.text("""
        UPDATE lcode
        SET language_count = s.c
        FROM (
            SELECT domainelement_pk, count(distinct(language_pk)) AS c
            FROM value
            JOIN valueset ON valueset.pk = valueset_pk
            WHERE domainelement_pk IS NOT NULL
            GROUP BY domainelement_pk
        ) AS s
        WHERE lcode.pk = s.domainelement_pk
    """))

    # language representation for c-parameters
    DBSession.execute(sqlalchemy.text("""
        UPDATE cparameter
        SET language_count = s.c
        FROM (
            SELECT unitparameter_pk, count(distinct(language_pk)) AS c
            FROM unitvalue
            JOIN unit ON unit.pk = unitvalue.unit_pk
            GROUP BY unitparameter_pk
        ) AS s
        WHERE cparameter.pk = s.unitparameter_pk
    """))

    # language representation for c-parameter codes
    DBSession.execute(sqlalchemy.text("""
        UPDATE ccode
        SET language_count = s.c
        FROM (
            SELECT unitdomainelement_pk, count(distinct(language_pk)) AS c
            FROM unitvalue
            JOIN unit ON unit.pk = unitvalue.unit_pk
            WHERE unitdomainelement_pk IS NOT NULL
            GROUP BY unitdomainelement_pk
        ) AS s
        WHERE ccode.pk = s.unitdomainelement_pk
    """))

    # examples per language
    DBSession.execute(sqlalchemy.text("""
        UPDATE variety
        SET example_count = s.c
        FROM (
            SELECT language_pk, count(sentence.pk) AS c
            FROM sentence
            GROUP BY language_pk
        ) AS s
        WHERE variety.pk = s.language_pk
    """))

    DBSession.flush()
    print('... done')

    print('Making pretty colourful dots for parameter values...')
    all_icons = [icon.name for icon in ORDERED_ICONS]

    code_query = DBSession.query(common.DomainElement)\
        .order_by(common.DomainElement.parameter_pk, common.DomainElement.id)
    for _, param_codes in groupby(code_query, lambda c: c.parameter_pk):
        icons = cycle(all_icons)
        for code in param_codes:
            code.update_jsondata(icon=next(icons))

    DBSession.flush()
    print('... done')
