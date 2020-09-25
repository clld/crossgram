<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<% from clld.db.meta import DBSession %>
<% import crossgram.models as m %>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "languages" %>
<%block name="title">${_('Language')} ${ctx.name}</%block>

<h2>${_('Language')} ${ctx.name}</h2>

<%
    construction_list = list(
        DBSession.query(m.Construction)
            .join(h.models.Contribution)
            .filter(m.Construction.language == ctx)
            .order_by(m.Construction.name))
%>
% if construction_list:
<h3>Constructions</h3>

<ul>
% for constr in construction_list:
  <li>${h.link(request, constr)} (from ${h.link(request, constr.contribution)})</li>
% endfor
</ul>

<h3>${_('Parameter')} Values</h3>
% endif

${request.get_datatable('values', h.models.Value, language=ctx).render()}

<%def name="sidebar()">
    ${util.language_meta()}
</%def>
