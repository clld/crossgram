<%inherit file="../snippet.mako"/>
<%namespace name="util" file="../util.mako"/>

% if ctx.description:
<p>
    ${ctx.description}
</p>
% endif

% if ctx.domain:
Possible values:
<% total = 0 %>
<table class="table table-hover table-condensed domain" style="width: auto;">
    <thead>
        <tr>
            <th>Value</th><th>No. of Constructions</th>
        </tr>
    </thead>
    <tbody>
        % for de in ctx.domain:
        <tr>
            <% total += (de.language_count or 0) %>
            <td>${de.description or de.name}</td>
            <td class="right">${de.language_count or 0}</td>
        </tr>
        % endfor
        <tr>
            <td class="right"><b>Total:</b></td><td class="right">${total}</td>
        </tr>
    </tbody>
</table>
% else:
<p><strong>Representation:</strong> ${ctx.language_count or 0}</p>
% endif
