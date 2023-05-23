<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<% from clld.db.meta import DBSession %>
<% import crossgram.models as m %>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "languages" %>
<%block name="title">${_('Language')} ${ctx.name}</%block>

<h2>${_('Language')}: ${ctx.name}</h2>

<div class="tabbable">

  ## apparently units don't have backlinks to languages
  <%
    construction_count = (
        DBSession.query(h.models.Unit)
            .filter(m.Unit.language_pk == ctx.pk)
            .count())
  %>
  <ul class="nav nav-tabs">
    <li class="active"><a href="#about" data-toggle="tab">Introduction</a></li>
    % if ctx.valuesets:
      <li><a href="#lparams" data-toggle="tab">${_('Parameters')}</a></li>
    % endif
    % if construction_count:
      <li><a href="#constr" data-toggle="tab">${_('Units')}</a></li>
    % endif
    % if ctx.example_count:
      <li><a href="#examples" data-toggle="tab">${_('Sentences')}</a></li>
    % endif
    ## % if ctx.sources:
    ##   <li><a href="#sources" data-toggle="tab">${_('Sources')}</a></li>
    ## % endif
  </ul>

  <div class="tab-content">

    <div id="about" class="tab-pane active">
      <div class="span8">
        ## TODO: very empty!
        ${ctx.description or ''|n}
      </div>
      <div class="span4">
        ${util.language_meta()}
      </div>
    </div>

    % if ctx.valuesets:
    <div id="lparams" class="tab-pane">
      ${request.get_datatable('values', h.models.Value, language=ctx).render()}
    </div>
    % endif

    % if construction_count:
    <div id="constr" class="tab-pane">
      ${request.get_datatable('units', m.Construction, language=ctx).render()}
    </div>
    % endif

    % if ctx.example_count:
    <div id="examples" class="tab-pane">
      ${request.get_datatable('sentences', h.models.Sentence, language=ctx).render()}
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
