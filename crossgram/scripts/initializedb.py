from __future__ import unicode_literals

import pathlib
import sys

from datetime import date

from clld.scripts.util import initializedb, Data
from clld.db.meta import DBSession
from clld.db.models import common

import crossgram
from crossgram import models
from crossgram.lib.cldf import load_cldfbench
from crossgram.lib.glottocode import make_glottocode_index


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

    # TODO less hard-coding of paths etc.

    print('Building glottocode index...', end='')
    glottocode_index = make_glottocode_index(
        pathlib.Path.home() / 'repos' / 'glottolog' / 'glottolog')
    print('done.')

    data = Data()

    for repo_path in (
        pathlib.Path.home() / 'repos' / 'crossgram' / 'comparison',
        pathlib.Path.home() / 'repos' / 'cldf-datasets' / 'petersonsouthasia',
    ):
        print("Loading submission '{}'...".format(repo_path), end='')
        submission = load_cldfbench(repo_path, glottocode_index)
        submission.add_to_database(data)
        print('done.')


def prime_cache(args):
    """If data needs to be denormalized for lookup, do that here.
    This procedure should be separate from the db initialization, because
    it will have to be run periodically whenever data has been updated.
    """


if __name__ == '__main__':  # pragma: no cover
    initializedb(create=main, prime_cache=prime_cache)
    sys.exit(0)
