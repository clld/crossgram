<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "unitparameters" %>
<%! import crossgram.models as m %>

<h2>${_('Unit Parameter')}: ${ctx.name or ctx.id}</h2>

<p><em>From ${_('Contribution')}: ${h.link(request, ctx.contribution)}</em></p>

% if ctx.description:
<p>${ctx.description}</p>
% endif

% if ctx.topic_assocs:
<%
  query = h.DBSession.query(m.UnitParameterTopic) \
    .join(m.UnitParameterTopic.topic) \
    .filter(m.UnitParameterTopic.unitparameter_pk == ctx.pk) \
    .order_by(m.Topic.name)
%>
<p><b>Topics:</b></p>
<ul>
% for assoc in query:
  <li>${h.link(request, assoc.topic)}</li>
% endfor
</ul>
% endif

<div>
    <% dt = request.registry.getUtility(h.interfaces.IDataTable, 'unitvalues'); dt = dt(request, h.models.UnitValue, unitparameter=ctx) %>
    ${dt.render()}
</div>
