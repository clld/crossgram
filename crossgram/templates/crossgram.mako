<%inherit file="app.mako"/>

<%block name="brand">
    <a href="${request.route_url('dataset')}" class="brand">
        ## TODO: remove 'beta'
        <img alt="CrossGram (beta)" src="${request.static_url('crossgram:static/crossgram-logo.png')}" />
    </a>
</%block>

${next.body()}
