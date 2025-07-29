<%inherit file="../snippet.mako"/>
<%namespace name="util" file="../util.mako"/>

% if request.params.get('parameter'):
    ## called for the info windows on parameter maps
    <% valueset = h.get_valueset(request, ctx) %>
    <h3>${h.link(request, ctx)}</h3>
    % if valueset:
        <h4>${_('Value')}</h4>
        <ul class='unstyled'>
            % for value in valueset.values:
            <li>
                ${h.map_marker_img(request, value)}
                ${h.link(request, valueset, label=str(value))}
                ${h.format_frequency(request, value)}
                % if value.description:
                <span>: ${value.description}</span>
                % endif
            </li>
            % endfor
        </ul>
        % if valueset.references:
            <h4>${_('Source')}</h4>
            <p>${h.linked_references(request, valueset)}</p>
        % endif
    % endif
% else:
<h3>${h.link(request, ctx)}</h3>
    % if ctx.description:
        <p>${ctx.description}</p>
    % endif
${h.format_coordinates(ctx)}
% endif
