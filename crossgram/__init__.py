from functools import partial

from pyramid.config import Configurator
from clld_glottologfamily_plugin import util
from clld.interfaces import IDomainElement, IMapMarker, IValueSet, IValue
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


# class LanguageByFamilyMapMarker(util.LanguageByFamilyMapMarker):
#     def get_icon(self, ctx, req):
#         if IValue.providedBy(ctx):
#             ctx = ctx.valueset.language
#         if IValueSet.providedBy(ctx):
#             ctx = ctx.language
#         return LanguageByFamilyMapMarker.get_icon(self, ctx, req)


# class LanguageByFamilyMapMarker(util.LanguageByFamilyMapMarker):
#     def __call__(self, ctx, req):
#         if IValueSet.providedBy(ctx):
#             c = collections.Counter([v.domainelement.jsondata['color'] for v in ctx.values])
#             return data_url(pie(*list(zip(*[(v, k) for k, v in c.most_common()])), **dict(stroke_circle=True)))
#         if IDomainElement.providedBy(ctx):
#             return data_url(icon(ctx.jsondata['color'].replace('#', 'c')))
#         if IValue.providedBy(ctx):
#             return data_url(icon(ctx.domainelement.jsondata['color'].replace('#', 'c')))


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.include('clld.web.app')
    config.include('clld_glottologfamily_plugin')
    config.registry.registerUtility(util.LanguageByFamilyMapMarker(), IMapMarker)

    config.register_menu(
        ('dataset', partial(menu_item, 'dataset', label='Home')),
        ('contributions', partial(menu_item, 'contributions')),
        ('contributors', partial(menu_item, 'contributors')),
        ('units', partial(menu_item, 'units')),
        ('unitparameters', partial(menu_item, 'unitparameters', label='C-Parameters')),
        ('parameters', partial(menu_item, 'parameters', label='L-Parameters')),
        ('languages', partial(menu_item, 'languages')),
        ('sentences', partial(menu_item, 'sentences')),
    )

    return config.make_wsgi_app()
