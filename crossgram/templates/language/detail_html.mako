<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<% import crossgram.models as m %>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "languages" %>
<%block name="title">${_('Language')} ${ctx.name}</%block>

<h2>${_('Language')}: ${ctx.name}</h2>

## copy of util.language_meta with stuff I don't need turned off
<%def name="language_meta(lang)">
 <div class="accordion" id="sidebar-accordion">
 % if getattr(request, 'map', False):
 <%util:accordion_group eid="acc-map" parent="sidebar-accordion" title="${_('Map')}" open="${True}">
   ${request.map.render()}
   ${h.format_coordinates(lang)}
 </%util:accordion_group>
 % endif
 % if lang.sources:
 <%util:accordion_group eid="sources" parent="sidebar-accordion" title="${_('Sources')}">
   <ul>
     % for source in lang.sources:
     <li>${h.link(request, source, label=source.description)}<br />
     <small>${h.link(request, source)}</small></li>
     % endfor
   </ul>
 </%util:accordion_group>
 % endif
 </div>
</%def>

<div class="tabbable">

  ## apparently units don't have backlinks to languages
  <%
    construction_count = (
        request.db.query(h.models.Unit)
            .filter(m.Unit.language_pk == ctx.pk)
            .count())
  %>
  <ul class="nav nav-tabs">
    <li class="active"><a href="#about" data-toggle="tab">About</a></li>
    % if ctx.valuesets:
      <li><a href="#lparams" data-toggle="tab">${_('Parameters')}</a></li>
    % endif
    % if construction_count:
      <li><a href="#constr" data-toggle="tab">${_('Units')}</a></li>
    % endif
    % if ctx.example_count:
      <li><a href="#examples" data-toggle="tab">${_('Sentences')}</a></li>
    % endif
    % if ctx.references:
      <li><a href="#sources" data-toggle="tab">${_('Sources')}</a></li>
    % endif
  </ul>

  <div class="tab-content">

    <div id="about" class="tab-pane active">
      <div class="span8">
        ${ctx.description or ''|n}
        <dl>
          % if ctx.glottolog_id:
          <dt>Glottocode:</dt>
          <dd>${h.external_link('http://glottolog.org/resource/languoid/id/{}'.format(ctx.glottolog_id), label=ctx.glottolog_id)}</dt>
          % endif
          <dt>Language family:</dt>
          <dd>${ctx.family.name if ctx.family else 'Isolate'}</dt>
        </dl>
        % if ctx.custom_names:
        <h3>Contributions</h3>
        <ul>
          <%
            name_query = request.db\
              .query(m.ContributionLanguage)\
              .join(m.CrossgramData)\
              .filter(m.ContributionLanguage.language_pk == ctx.pk)
          %>
          % for contrib_lang in name_query:
          <li>
            ${h.link(request, contrib_lang.contribution)}
            % if contrib_lang.custom_language_name != ctx.name:
              (Contribution-specific name: ${contrib_lang.custom_language_name})
            % endif
          </li>
          % endfor
        </ul>
        % endif
      </div>
      <div class="span4">
        ${language_meta(ctx)}
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

    % if ctx.references:
    <div id="sources" class="tab-pane">
      ${request.get_datatable('sources', m.CrossgramDataSource, language=ctx).render()}
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
