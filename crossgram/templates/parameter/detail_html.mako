<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "parameters" %>
<%! import crossgram.models as m %>
<%block name="title">${_('Parameter')} ${ctx.name}</%block>

<h2>${_('Parameter')}: ${ctx.name or ctx.id}</h2>

<p><em>From ${_('Contribution')}: ${h.link(request, ctx.contribution)}</em></p>

% if ctx.description:
<p>${ctx.description}</p>
% endif

% if ctx.topic_assocs:
<%
  query = h.DBSession.query(m.ParameterTopic) \
    .join(m.ParameterTopic.topic) \
    .filter(m.ParameterTopic.parameter_pk == ctx.pk) \
    .order_by(m.Topic.name)
%>
<p><b>Topics:</b></p>
<ul>
% for assoc in query:
  <li>${h.link(request, assoc.topic)}</li>
% endfor
</ul>
% endif

% if map_ or request.map:
${(map_ or request.map).render()}
% endif

${request.get_datatable('values', h.models.Value, parameter=ctx).render()}
