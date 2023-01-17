<%inherit file="app.mako"/>

##
## define app-level blocks:
##
## <%block name="header">
##     <a href="${request.route_url('dataset')}">
##         <img src="${request.static_url('crossgram:static/header.gif')}"/>
##     </a>
## </%block>

<%block name="brand">
    <a href="${request.route_url('dataset')}" class="brand">
        <img alt="CrossGram" src="${request.static_url('crossgram:static/crossgram-logo.png')}" />
    </a>
</%block>

${next.body()}
