<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "contributions" %>
<%block name="title">${_('Contributions')}</%block>

<h2>${_('Contributions')}</h2>

<p><em>See also: <a href="${req.route_url('contributors')}">List of all ${_('Contributors')}</a></em>.</p>

<div>
    ${ctx.render()}
</div>
