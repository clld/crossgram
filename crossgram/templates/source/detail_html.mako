<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "sources" %>
<%block name="title">${ctx.name}</%block>
<%! from crossgram import models %>

<h2>${ctx.name}</h2>
${ctx.coins(request)|n}

<div class="tabbable">
    <ul class="nav nav-tabs">
        <li class="active"><a href="#tab1" data-toggle="tab">Text</a></li>
        <li><a href="#tab2" data-toggle="tab">BibTeX</a></li>
    </ul>
    <div class="tab-content">
        <% bibrec = ctx.bibtex() %>
        <div id="tab1" class="tab-pane active">
            <p id="${h.format_gbs_identifier(ctx)}">${bibrec.text()}</p>
            % if ctx.datadict().get('Additional_information'):
            <p>
                ${ctx.datadict().get('Additional_information')}
            </p>
            % endif
            % if bibrec.get('url'):
                <p>${h.external_link(bibrec['url'])}</p>
            % endif
            ${util.gbs_links(filter(None, [ctx.gbs_identifier]))}
            % if ctx.jsondata.get('internetarchive_id'):
                <hr />
                <iframe src='https://archive.org/stream/${ctx.jsondata.get('internetarchive_id')}?ui=embed#mode/1up' width='680px' height='750px' frameborder='1' ></iframe>
            % endif
        </div>
        <div id="tab2" class="tab-pane"><pre>${bibrec}</pre></div>
    </div>
</div>

<%def name="sidebar()">
  <div class="span12">
    <div class="well well-small">
      <p><b>Contribution:</b> ${h.link(request, ctx.contribution)}</p>
      % if ctx.languagereferences:
      <%
        lang_assocs = h.DBSession.query(models.LanguageReference, models.ContributionLanguage) \
          .join(models.LanguageReference.language) \
          .join(
            models.ContributionLanguage,
            models.ContributionLanguage.language_pk == models.LanguageReference.language_pk,
            isouter=True) \
          .filter(models.ContributionLanguage.contribution_pk == ctx.contribution_pk) \
          .filter(models.LanguageReference.source_pk == ctx.pk)
      %>
      <p><b>Languages:</b></p>
      <ul>
      % for lang_assoc, contrib_lang in lang_assocs:
        <li>${h.link(request, lang_assoc.language, label=contrib_lang.custom_language_name)}</li>
      % endfor
      <ul>
      % endif
    </div>
  </div>
</%def>
