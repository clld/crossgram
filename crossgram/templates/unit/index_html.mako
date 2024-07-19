<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "units" %>
<%block name="title">${_('Units')}</%block>

<h2>${_('Units')}</h2>

<p><em>See also: <a href="${req.route_url('unitparameters')}">List of all ${_('Unit Parameters')}</a></em>.</p>

<div>
  ${ctx.render()}
</div>
