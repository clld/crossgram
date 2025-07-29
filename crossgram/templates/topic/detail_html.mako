<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "topics" %>
<% import crossgram.models as m %>
<%block name="title">${_('Topic')} ${ctx.name or ctx.id}</%block>

<h2>${_('Topic')}: ${ctx.name or ctx.id}</h2>

% if ctx.description:
<p>${ctx.description}</p>
% endif

## TODO(johannes): could be in a side panel
% if ctx.grammacode or ctx.sil_counterpart or ctx.wikipedia_counterpart:
<dl>
  % if ctx.grammacode:
  <dt>Grammacode</dt>
  ## TODO(johannes): link to grammaticon
  <dd>${ctx.grammacode}</dd>
  % endif
  % if ctx.sil_counterpart:
  <dt>SIL counter-part</dt>
  <dd>
    % if ctx.sil_url:
    ${h.external_link(ctx.sil_url, label=ctx.sil_counterpart)}
    % else:
    ${ctx.sil_counterpart}
    % endif
  </dd>
  % endif
  % if ctx.wikipedia_counterpart:
  <dt>Wikipedia counter-part</dt>
  <dd>
    % if ctx.wikipedia_url:
    ${h.external_link(ctx.wikipedia_url, label=ctx.wikipedia_counterpart)}
    % else:
    ${ctx.wikipedia_counterpart}
    % endif
  </dd>
  % endif
</dl>
% endif

% if ctx.parameter_assocs:
<h3>Associated ${_('Parameters')}</h3>
<% query = h.DBSession.query(m.LParameter) \
     .join(m.ParameterTopic) \
     .join(m.LParameter.contribution) \
     .filter(m.ParameterTopic.topic == ctx) \
     .distinct()
%>
<ul>
  % for param in query:
  <li>${h.link(req, param)} (from ${h.link(req, param.contribution)})</li>
  % endfor
</ul>
% endif

% if ctx.unitparameter_assocs:
<h3>Associated ${_('Unit Parameters')}</h3>
<% query = h.DBSession.query(m.CParameter) \
     .join(m.UnitParameterTopic) \
     .join(m.CParameter.contribution) \
     .filter(m.UnitParameterTopic.topic == ctx) \
     .distinct()
%>
<ul>
  % for param in query:
  <li>${h.link(req, param)} (from ${h.link(req, param.contribution)})</li>
  % endfor
</ul>
% endif
