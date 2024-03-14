<%inherit file="../snippet.mako"/>
<%namespace name="util" file="../util.mako"/>

% if ctx.description:
<p>
    ${ctx.description}
</p>
% endif

% if ctx.domain:
<% total = 0 %>
<table class="table table-hover table-condensed domain" style="width: auto;">
    <thead>
        <tr>
            <th>&#160;</th><th>Value</th><th>Representation</th>
        </tr>
    </thead>
    <tbody>
        % for de in ctx.domain:
        <tr>
            <% total += (de.language_count or 0) %>
            <td>${h.map_marker_img(request, de)}</td>
            <td>${de.name}</td>
            <td class="right">${de.language_count or 0}</td>
        </tr>
        % endfor
        <tr>
            <td colspan="2" class="right"><b>Total:</b></td><td class="right">${total}</td>
        </tr>
    </tbody>
</table>
% else:
<p><strong>Representation:</strong> ${ctx.language_count or 0}</p>
% endif
