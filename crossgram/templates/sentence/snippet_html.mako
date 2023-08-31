<%inherit file="../snippet.mako"/>
<%namespace name="util" file="../util.mako"/>

${h.rendered_sentence(ctx)}

% if ctx.references or ctx.source:
<dl>
<dt>${_('Source')}:</dt>
% if ctx.source:
<dd>${ctx.source}</dd>
% endif
% if ctx.references:
<dd>${h.linked_references(request, ctx)|n}</dd>
% endif
</dl>
% endif
