from __future__ import unicode_literals

import pathlib
import sys

from datetime import date

from clld.scripts.util import initializedb, Data
from clld.db.meta import DBSession
from clld.db.models import common
from clldutils import jsonlib

import crossgram
from crossgram import models
from crossgram.lib.cldf import CLDFBenchSubmission


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

    data = Data()
    language_id_map = {}
    for contrib_md in jsonlib.load('contributions.json')['contributions']:
        print('Loading submission', contrib_md['id'], '...')
        submission = CLDFBenchSubmission.load(contrib_md)
        submission.add_to_database(data, language_id_map)
        print('... done')


def prime_cache(args):
    """If data needs to be denormalized for lookup, do that here.
    This procedure should be separate from the db initialization, because
    it will have to be run periodically whenever data has been updated.
    """


if __name__ == '__main__':  # pragma: no cover
    initializedb(create=main, prime_cache=prime_cache)
    sys.exit(0)
