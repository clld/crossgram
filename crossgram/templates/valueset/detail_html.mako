<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "contributions" %>
<%block name="title">${_('Value')} ${ctx.language.name}/${ctx.parameter.name}</%block>

% if ctx.values:
<% value = ctx.values[0] %>
<h2>${_('Value')} ${value.domainelement.name if value.domainelement else value.name}</h2>
% else:
<% value = None %>
<h2>${_('Value Set')} ${h.link(request, ctx.language)}/${h.link(request, ctx.parameter)}</h2>
% endif

% if value and (value.markup_description or value.description):
${h.text2html(h.Markup(value.markup_description) if value.markup_description else value.description, mode='p')}
% elif ctx.markup_description or ctx.description:
${h.text2html(h.Markup(ctx.markup_description) if ctx.markup_description else ctx.description, mode='p')}
% endif

<dl>
  <dt>${_('Contribution')}:</dt>
  <dd>${h.link(request, ctx.contribution)}</dd>
  <dt>${_('Language')}:</dt>
  <dd>${h.link(request, ctx.language)}</dd>
  <dt>${_('Parameter')}:</dt>
  <dd>${h.link(request, ctx.parameter)}</dd>
  % if ctx.references or ctx.source:
  <dt class="source">${_('Source')}:</dt>
  % if ctx.references:
  <dd class="source">${h.linked_references(request, ctx)|n}</dd>
  % elif ctx.source:
  <dd>${ctx.source}</dd>
  % endif
  % endif
  % for k, v in ctx.datadict().items():
  <dt>${k}</dt>
  <dd>${v}</dd>
  % endfor
</dl>

% if value and value.sentence_assocs:
<h3>${_('Sentences')}</h3>
${util.sentences(value)}
% endif
