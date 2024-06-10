<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "unitparameters" %>

<h2>${_('Unit Value')}: ${ctx.unitdomainelement.name if ctx.unitdomainelement else ctx.name}</h2>

% if ctx.markup_description or ctx.description:
${h.text2html(h.Markup(ctx.markup_description) if ctx.markup_description else ctx.description, mode='p')}
% endif

<dl>
  <dt>${_('Contribution')}:</dt>
  <dd>${h.link(request, ctx.contribution)}</dd>
  <dt>${_('Language')}:</dt>
  <dd>${h.link(req, obj=ctx.unit.language)}</dd>
  <dt>${_('Unit')}:</dt>
  <dd>${h.link(req, obj=ctx.unit)}</dd>
  <dt>${_('Unit Parameter')}:</dt>
  <dd>${h.link(req, obj=ctx.unitparameter)}</dd>
</dl>

% if ctx.sentence_assocs:
<h3>${_('Sentences')}</h3>
${util.sentences(ctx)}
% endif
