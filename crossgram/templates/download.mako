<%inherit file="home_comp.mako"/>
<%namespace name="util" file="util.mako"/>
<%! from clld.db.meta import DBSession %>
<%! from crossgram import models %>

<h3>Downloads</h3>

<p>
    All datasets on GrossGram are available as <a
    href="https://cldf.clld.org">CLDF</a> datasets.
    The datasets are maintained using the version control system
    <a href="https://git-scm.com"><em>git</em></a> and make public using
    a hosting site for git repositories – usually
    <a href="https://github.com/cldf-datasets">Github</a>.
    Citeable snapshots of the datasets reside on
    <a href="https://zenodo.org/communities/cldf-datasets">Zenodo</a> and can
    be downloaded by following the DOI links below.
</p>

<table class="table table-nonfluid table-condensed">
    <thead>
    <tr>
        <th>dictionary</th>
        <th>author</th>
        <th>Git repository</th>
        <th>DOI</th>
    </tr>
    </thead>
    <tbody>
        % for contrib in DBSession.query(models.CrossgramData).order_by(models.CrossgramData.number):
            <tr>
                <td>${contrib}</td>
                <td>${contrib.formatted_contributors()}</td>
                <td>
                    % if contrib.git_repo:
                    <a href="${contrib.git_repo}">
                        ${contrib.git_repo}
                    </a>
                    % endif
                </td>
                <td>
                    % if contrib.doi:
                    <a href="https://doi.org/${contrib.doi}">
                        <img src="https://zenodo.org/badge/DOI/${contrib.doi}.svg" alt="DOI">
                    </a>
                    % endif
                </td>
            </tr>
        % endfor
    </tbody>
</table>
