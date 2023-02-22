import itertools
from functools import partial

from pyramid.config import Configurator
from clld import interfaces
from clld.web.app import menu_item
from clld_glottologfamily_plugin import util

# we must make sure custom models are known at database initialization!
from crossgram import models, md


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


class LanguageByFamilyMapMarker(util.LanguageByFamilyMapMarker):
    def get_icon(self, ctx, req):
        if interfaces.IValueSet.providedBy(ctx):
            icons = [
                v.domainelement.jsondata['icon']
                for v in ctx.values
                if v.domainelement]
            # FIXME this only shows the *first* value
            return icons[0] if len(icons) > 0 else None
        elif interfaces.IValue.providedBy(ctx) and ctx.domainelement:
            return ctx.domainelement.jsondata['icon']
        else:
            return super().get_icon(ctx, req)


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.include('clld.web.app')
    config.include('clld_glottologfamily_plugin')
    config.registry.registerUtility(
        LanguageByFamilyMapMarker(), interfaces.IMapMarker)

    config.register_menu(
        #('dataset', partial(menu_item, 'dataset', label='Home')),
        ('contributions', partial(menu_item, 'contributions')),
        ('languages', partial(menu_item, 'languages')),
        ('parameters', partial(menu_item, 'parameters', label='L-Parameters')),
        ('units', partial(menu_item, 'units')),
        #('unitparameters', partial(menu_item, 'unitparameters', label='C-Parameters')),
        ('sentences', partial(menu_item, 'sentences')),
        ('contributors', partial(menu_item, 'contributors')),
    )

    for if_ in [interfaces.IRepresentation, interfaces.IMetadata]:
        config.register_adapter(
            md.BibTex, interfaces.IContribution, if_, name=md.BibTex.mimetype)

    return config.make_wsgi_app()
