<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "contributions" %>

<h2>${_('Contribution')}: ${ctx.name}</h2>

<p>by ${h.linked_contributors(request, ctx)}</p>

<div class="tabbable">

    <ul class="nav nav-tabs">
        <li class="active"><a href="#about" data-toggle="tab">Introduction</a></li>
        % if ctx.constructions:
            <li><a href="#constr" data-toggle="tab">${_('Units')}</a></li>
        % endif
        % if ctx.cparameters:
            <li><a href="#cparams" data-toggle="tab">${_('Unit Parameters')}</a></li>
        % endif
        % if ctx.lparameters:
            <li><a href="#lparams" data-toggle="tab">${_('Parameters')}</a></li>
        % endif
        % if ctx.examples:
            <li><a href="#examples" data-toggle="tab">${_('Sentences')}</a></li>
        % endif
        % if ctx.sources:
            <li><a href="#sources" data-toggle="tab">${_('Sources')}</a></li>
        % endif
    </ul>

    <div class="tab-content">
        <div id="about" class="tab-pane active">
            <div class="span8">
                ${util.files()}
                ${util.data()}
                <div class="intro">
                    ${ctx.markup_description or ''|n}
                </div>
            </div>
            <div class="span4">
                <div class="well well-small">
                    ${ctx.toc or ''|n}
                </div>
            </div>
        </div>
        % if ctx.constructions:
        <div id="constr" class="tab-pane">
            ${request.get_datatable('units', h.models.Unit, crossgramdata=ctx).render()}
        </div>
        % endif
        % if ctx.cparameters:
        <div id="cparams" class="tab-pane">
            ${request.get_datatable('unitparameters', h.models.UnitParameter, crossgramdata=ctx).render()}
        </div>
        % endif
        % if ctx.lparameters:
        <div id="lparams" class="tab-pane">
            ${request.get_datatable('parameters', h.models.Parameter, crossgramdata=ctx).render()}
        </div>
        % endif
        % if ctx.examples:
        <div id="examples" class="tab-pane">
            ${request.get_datatable('sentences', h.models.Sentence, crossgramdata=ctx).render()}
        </div>
        % endif
        % if ctx.sources:
        <div id="sources" class="tab-pane">
            ${request.get_datatable('sources', h.models.Source, crossgramdata=ctx).render()}
        </div>
        % endif
    </div>

    <script>
$(document).ready(function() {
    if (location.hash !== '') {
        $('a[href="#' + location.hash.substr(2) + '"]').tab('show');
    }
    return $('a[data-toggle="tab"]').on('shown', function(e) {
        return location.hash = 't' + $(e.target).attr('href').substr(1);
    });
});
    </script>

</div>
