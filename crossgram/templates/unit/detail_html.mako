<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "units" %>


<h2>${_('Unit')} ${ctx.name}</h2>

<p><em>From ${_('Contribution')}: ${h.link(request, ctx.contribution)}</em></p>

% if ctx.description:
<p>
    ${ctx.description}
</p>
% endif

% if ctx.references:
<p>
    <em>Sources:</em>
    ${h.linked_references(request, ctx)|n}
</p>
% endif

<dl>
% for key, objs in h.groupby(ctx.data, lambda o: o.key):
<dt>${key}</dt>
    % for obj in sorted(objs, key=lambda o: o.ord):
    <dd>${obj.value}</dd>
    % endfor
% endfor
</dl>

% if ctx.sentence_assocs:
<p><strong>${_('Sentences')}</strong></p>
<ol>
%   for a in ctx.sentence_assocs:
    <li>
        ${h.rendered_sentence(a.sentence)}
        % if a.sentence.references:
        <p><em>See</em> ${h.linked_references(request, a.sentence)}</p>
        % endif
    </li>
%   endfor
</ol>
% endif

${request.get_datatable('unitvalues', h.models.UnitValue, unit=ctx).render()}
