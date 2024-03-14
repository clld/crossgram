<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "topics" %>
<%block name="title">${_('Topic')} ${ctx.name}</%block>

<h2>${_('Topic')}: ${ctx.name or ctx.id}</h2>

% if ctx.description:
<p>${ctx.description}</p>
% endif

## TODO: could be in a side panel
% if ctx.croft_counterpart or ctx.wikipedia_counterpart:
<dl>
  % if ctx.gold_counterpart:
  <dt>Croft counter-part</dt>
  <dd>
    ${ctx.croft_counterpart}
    % if ctx.gold_comment:
      <br>${ctx.croft_definition}
    % endif
  </dd>
  % endif
  % if ctx.isocat_counterpart:
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

## TODO: table with associated parameters
