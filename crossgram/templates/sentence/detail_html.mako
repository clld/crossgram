<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "sentences" %>
<%block name="title">Example ${ctx.id}</%block>

<%def name="sidebar()">
    <%util:well>
        <dl>
            <dt>Contribution</dt>
            <dd>${h.link(request, ctx.contribution)}</dd>
            <dt>Language</dt>
            <dd>${h.link(request, ctx.language)}</dd>
            % if ctx.value_assocs:
            <dt>${_('Language')} datapoints</dt>
            <dd>
                <ul>
                    % for va in ctx.value_assocs:
                        % if va.value:
                    <li>${h.link(request, va.value.valueset, label=f'{va.value.valueset.parameter.name}: {va.value.domainelement.name if va.value.domainelement else va.value.name}')}</li>
                        % endif
                    % endfor
                </ul>
            </dd>
            % endif
            % if ctx.unit_assocs:
            <dt>${_('Units')}</dt>
            <dd>
                <ul>
                    % for va in ctx.unit_assocs:
                        % if va.unit:
                    <li>${h.link(request, va.unit)}</li>
                        % endif
                    % endfor
                </ul>
            </dd>
            % endif
            % if ctx.unitvalue_assocs:
            <dt>${_('Unit')} datapoints</dt>
            <dd>
                <ul>
                    % for va in ctx.unitvalue_assocs:
                        % if va.unitvalue:
                    <li>${h.link(request, va.unitvalue, label=f'{va.unitvalue.unitparameter.name}: {va.unitvalue.domainelement.name if va.unitvalue.domainelement else va.unitvalue.name}')}</li>
                        % endif
                    % endfor
                </ul>
            </dd>
            % endif
        </dl>
    </%util:well>
</%def>

<h2>${_('Sentence')} ${ctx.id}</h2>

${h.rendered_sentence(ctx)|n}

<dl>
% if ctx.comment:
<dt>Comment:</dt>
<dd>${ctx.markup_comment or ctx.comment|n}</dd>
% endif
% if ctx.source and ctx.type:
<dt>${_('Type')}:</dt>
<dd>${ctx.type}</dd>
% endif
% if ctx.references or ctx.source:
<dt>${_('Source')}:</dt>
% if ctx.source:
<dd>${ctx.source}</dd>
% endif
% if ctx.references:
<dd>${h.linked_references(request, ctx)|n}</dd>
% endif
% endif
</dl>
