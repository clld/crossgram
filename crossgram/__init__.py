from functools import partial
from itertools import chain

from pyramid.config import Configurator
# apparently the `from crossgram.interfaces import` clause below shadows this
# import???
from clld import interfaces as common_interfaces
from clld.db.meta import DBSession
from clld.db.models import common
from clld.web.app import menu_item
from clld.web.icon import ICON_MAP, Icon
from clld_glottologfamily_plugin import util

# we must make sure custom models are known at database initialization!
from crossgram import models, md  # noqa: F401
from crossgram.interfaces import ITopic


_ = lambda s: s  # noqa: E731
_('Sentence')
_('Sentences')
_('Contributor')
_('Contributors')
_('Contribution')
_('Contributions')
_('Parameter')
_('Parameters')
_('Topic')
_('Topics')
_('Unit')
_('Units')
_('Unit Parameter')
_('Unit Parameters')


class LanguageByFamilyMapMarker(util.LanguageByFamilyMapMarker):
    def get_icon(self, ctx, req):
        if common_interfaces.IValueSet.providedBy(ctx):
            icons = [
                v.domainelement.jsondata['icon']
                for v in ctx.values
                if v.domainelement]
            # FIXME this only shows the *first* value
            return icons[0] if len(icons) > 0 else None
        elif common_interfaces.IValue.providedBy(ctx) and ctx.domainelement:
            return ctx.domainelement.jsondata['icon']
        elif common_interfaces.IDomainElement.providedBy(ctx):
            return ctx.jsondata['icon']
        else:
            return super().get_icon(ctx, req)


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.include('clld.web.app')
    config.include('clld_glottologfamily_plugin')
    config.registry.registerUtility(
        LanguageByFamilyMapMarker(), common_interfaces.IMapMarker)

    config.register_resource('topic', models.Topic, ITopic, with_index=True)

    custom_icons_names = {
        name: True
        for de in chain(
            DBSession.query(common.DomainElement),
            DBSession.query(common.UnitDomainElement))
        if (name := de.jsondata.get('icon')) and name not in ICON_MAP}
    for name in custom_icons_names:
        config.registry.registerUtility(
            Icon(name), common_interfaces.IIcon, name=name)

    config.register_menu(
        # ('dataset', partial(menu_item, 'dataset', label='Home')),
        ('contributions', partial(menu_item, 'contributions')),
        ('languages', partial(menu_item, 'languages')),
        ('parameters', partial(menu_item, 'parameters', label='L-Parameters')),
        ('units', partial(menu_item, 'units')),
        # ('unitparameters', partial(menu_item, 'unitparameters', label='C-Parameters')),
        ('sentences', partial(menu_item, 'sentences')),
        ('topics', partial(menu_item, 'topics')),
        ('sources', partial(menu_item, 'sources')),
        ('contributors', partial(menu_item, 'contributors')),
    )

    for if_ in [common_interfaces.IRepresentation, common_interfaces.IMetadata]:
        config.register_adapter(
            md.BibTex,
            common_interfaces.IContribution,
            if_,
            name=md.BibTex.mimetype)

    return config.make_wsgi_app()
