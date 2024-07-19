<%inherit file="../home_comp.mako"/>
<%block name="title">Home</%block>

## <%def name="sidebar()">
##     <div class="well">
##         <h3>Sidebar</h3>
##         <p>
##             Content
##         </p>
##     </div>
## </%def>

## TODO: remove 'beta'
<h2>Welcome to CrossGram<sup><em>beta</em></sup></h2>

<p>
  CrossGram is a publication repository for cross-linguistic data resulting from
  research on grammatical patterns in the world's languages.
  It is part of the CLLD series of projects
  (${h.external_link('https://clld.org/', label='Cross-Linguistic Linked Data')})
  hosted by the Max Planck Institute for Evolutionary Anthropology since 2008
  (lead developer: Robert Forkel).
</p>

<p>
  All CrossGram contributions conform to the CLDF standard
  (${h.external_link('https://cldf.clld.org/', label='Cross-Linguistic Data Formats')}).
  A CrossGram contribution has a title, a set of authors and a year of
  publication and can be cited as a separate publication, though it is usually
  associated with a standard journal or book publication.
</p>

<p>
  A CrossGram publication covers between 20 and 1200 languages, and it provides
  information about the languages (language parameters, l-parameters), or
  information about cross-linguistically comparable constructions (construction
  parameters, c-parameters).
  Each contribution includes bibliographical references about the languages, and
  some of the contributions include example sentences.
</p>

<p>
  CrossGram is edited by Martin Haspelmath in collaboration with Johannes
  Englisch (Max Planck Institute for Evolutionary Anthropology).
</p>
