<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "unitparameters" %>

<h2>${_('Unit Parameter')}: ${ctx.name or ctx.id}</h2>

## TODO: list of linked topics

<p><em>From ${_('Contribution')}: ${h.link(request, ctx.contribution)}</em></p>

<div>
    <% dt = request.registry.getUtility(h.interfaces.IDataTable, 'unitvalues'); dt = dt(request, h.models.UnitValue, unitparameter=ctx) %>
    ${dt.render()}
</div>
