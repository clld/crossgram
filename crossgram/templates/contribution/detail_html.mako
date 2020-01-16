<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "contributions" %>

<h2>${_('Contribution')}: ${ctx.name}</h2>

${util.data()}

<div class="tabbable">

    <ul class="nav nav-tabs">
        <li class="active"><a href="#about" data-toggle="tab">Introduction</a></li>
        <li><a href="#constr" data-toggle="tab">${_('Units')}</a></li>
        <li><a href="#cparams" data-toggle="tab">${_('Unit Parameters')}</a></li>
        <li><a href="#lparams" data-toggle="tab">${_('Parameters')}</a></li>
        <li><a href="#examples" data-toggle="tab">${_('Sentences')}</a></li>
    </ul>

    <div class="tab-content">
        <div id="about" class="tab-pane active">
            <div class="span8">
                ${util.files()}
                ${util.data()}
                ${ctx.description or ''|n}
            </div>
            <div class="span4">
                <div class="well well-small">
                    ${ctx.toc or ''|n}
                </div>
            </div>
        </div>
        <div id="constr" class="tab-pane">
            ${request.get_datatable('units', h.models.Unit, contribution=ctx).render()}
        </div>
        <div id="cparams" class="tab-pane">
            ${request.get_datatable('unitparameters', h.models.UnitParameter, contribution=ctx).render()}
        </div>
        <div id="lparams" class="tab-pane">
            ${request.get_datatable('parameters', h.models.Parameter, contribution=ctx).render()}
        </div>
        <div id="examples" class="tab-pane">
            ${request.get_datatable('sentences', h.models.Sentence, contribution=ctx).render()}
        </div>
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
