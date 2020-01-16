from functools import partial

from pyramid.config import Configurator
from clld.web.app import menu_item

# we must make sure custom models are known at database initialization!
from crossgram import models


_ = lambda s: s
_('Sentence')
_('Sentences')
_('Contributor')
_('Contributors')
_('Contribution')
_('Contributions')
_('Parameter')
_('Parameters')
_('Unit')
_('Units')
_('Unit Parameter')
_('Unit Parameters')


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.include('clld.web.app')

    config.register_menu(
        ('dataset', partial(menu_item, 'dataset', label='Home')),
        ('contributions', partial(menu_item, 'contributions')),
        ('contributors', partial(menu_item, 'contributors')),
        ('units', partial(menu_item, 'units')),
        ('unitparameters', partial(menu_item, 'unitparameters', label='C-Parameters')),
        ('languages', partial(menu_item, 'languages')),
        ('parameters', partial(menu_item, 'parameters', label='L-Parameters')),
        ('sentences', partial(menu_item, 'sentences')),
    )

    return config.make_wsgi_app()
