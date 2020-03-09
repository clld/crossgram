<%inherit file="../snippet.mako"/>
<%namespace name="util" file="../util.mako"/>

% if ctx.description:
<p>
    ${ctx.description}
</p>
% endif

% if ctx.domain:
Possible values:
<ul>
    % for de in ctx.domain:
    <li>${de.description or de.name}</li>
    % endfor
</ul>
% endif
