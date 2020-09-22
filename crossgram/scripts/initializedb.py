from __future__ import unicode_literals

import pathlib
import sys

from datetime import date

from clld.cliutil import Data
from clld.db.meta import DBSession
from clld.db.models import common
from clldutils import jsonlib
from clldutils.misc import slug

import git

import crossgram
from crossgram import models
from crossgram.lib.cldf import CLDFBenchSubmission
from crossgram.lib.cldf_zenodo import download_from_doi


def main(args):
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
    # TODO --internal switch for published and unpublished data
    submissions_path = internal_repo / 'submissions-internal'

    language_id_map = {}
    for contrib_dir in submissions_path.iterdir():
        contrib_md = jsonlib.load(contrib_dir / 'md.json')
        sid = contrib_md['id']

        if contrib_md.get('doi'):
            doi = contrib_md['doi']
            path = internal_repo / 'datasets' / '{}-{}'.format(sid, slug(doi))
            if not path.exists():
                print(
                    'Downloading submission', sid,
                    'from zenodo; doi:', doi)
                download_from_doi(doi, path)

        elif contrib_md.get('repo'):
            repo = contrib_md.get('repo')
            checkout = contrib_md.get('checkout')
            if checkout:
                # specific commit/tag/branch
                path = internal_repo / 'datasets' / '{}-{}'.format(sid, slug(checkout))
                if not path.exists():
                    print('Cloning', repo, 'into', path, '...')
                    git.Git().clone(repo, path)
                    print('Checking out commit', checkout, '...')
                    git.Git(str(path)).checkout(checkout)
            else:
                # latest commit on the default branch
                path = internal_repo / 'datasets' / sid
                if not path.exists():
                    print('Cloning', repo, 'into', path, '...')
                    git.Git().clone(repo, path)
                else:
                    print('Pulling latest commit in', path, '...')
                    git.Git(str(path)).pull()

        else:
            path = internal_repo / 'datasets' / sid

        if not path.exists():
            print('could not find folder', str(path))
            continue

        print('Loading submission', sid, '...')
        submission = CLDFBenchSubmission.load(path, contrib_md)
        submission.add_to_database(data, language_id_map)
        print('... done')


def prime_cache(args):
    """If data needs to be denormalized for lookup, do that here.
    This procedure should be separate from the db initialization, because
    it will have to be run periodically whenever data has been updated.
    """
