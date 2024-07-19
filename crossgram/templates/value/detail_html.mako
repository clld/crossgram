<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "contributions" %>
<%block name="title">${_('Value')} ${ctx.valueset.language.name}/${ctx.valueset.parameter.name}</%block>


<h2>${_('Value')} ${ctx.domainelement.name if ctx.domainelement else ctx.name}</h2>

% if ctx.markup_description or ctx.description:
${h.text2html(h.Markup(ctx.markup_description) if ctx.markup_description else ctx.description, mode='p')}
% endif

<dl>
  <dt>${_('Contribution')}:</dt>
  <dd>${h.link(request, ctx.valueset.contribution)}</dd>
  <dt>${_('Language')}:</dt>
  <dd>${h.link(request, ctx.valueset.language)}</dd>
  <dt>${_('Parameter')}:</dt>
  <dd>${h.link(request, ctx.valueset.parameter)}</dd>
  % if ctx.valueset.references or ctx.valueset.source:
  <dt class="source">${_('Source')}:</dt>
  % if ctx.valueset.references:
  <dd class="source">${h.linked_references(request, ctx)|n}</dd>
  % elif ctx.valueset.source:
  <dd>${ctx.valueset.source}</dd>
  % endif
  % endif
  % for k, v in ctx.datadict().items():
  <dt>${k}</dt>
  <dd>${v}</dd>
  % endfor
</dl>

% if ctx.sentence_assocs:
<h3>${_('Sentences')}</h3>
${util.sentences(ctx)}
% endif
