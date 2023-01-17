<%inherit file="app.mako"/>

<%block name="brand">
    <a href="${request.route_url('dataset')}" class="brand">
        <img alt="CrossGram" src="${request.static_url('crossgram:static/crossgram-logo.png')}" />
    </a>
</%block>

${next.body()}
