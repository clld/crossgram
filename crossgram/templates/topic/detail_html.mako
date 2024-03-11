<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "topics" %>
<%block name="title">${_('Topic')} ${ctx.name}</%block>

<h2>${_('Topic')}: ${ctx.name or ctx.id}</h2>

% if ctx.description:
<p>${ctx.description}</p>
% endif

## TODO: could be in a side panel
% if ctx.gold_counterpart or ctx.isocat_counterpart:
<dl>
  % if ctx.gold_counterpart:
  <dt>GOLD counter-part</dt>
  <dd>
    % if ctx.gold_url:
    ${h.external_link(ctx.gold_url, label=ctx.gold_counterpart)}
    % else:
    ${ctx.gold_counterpart}
    % endif
    % if ctx.gold_comment:
    <br>${ctx.gold_comment}
    % endif
  </dd>
  % endif
  % if ctx.isocat_counterpart:
  <dt>ISOCAT counter-part</dt>
  <dd>
    % if ctx.isocat_url:
    ${h.external_link(ctx.isocat_url, label=ctx.isocat_counterpart)}
    % else:
    ${ctx.isocat_counterpart}
    % endif
    % if ctx.isocat_comment:
    <br>${ctx.isocat_comment}
    % endif
  </dd>
  % endif
</dl>
% endif

## TODO: table with associated parameters
