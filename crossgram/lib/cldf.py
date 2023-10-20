from collections import defaultdict, namedtuple, OrderedDict
from itertools import chain, cycle
import re
import sys

from clld.cliutil import bibtex2source, Data
from clld.lib import bibtex
from clld.web.icon import ORDERED_ICONS
from clldutils import jsonlib
from clldutils.misc import slug
from nameparser import HumanName
from pycldf import iter_datasets

from clld.db.meta import DBSession
from clld.db.models import (
    ContributionContributor,
    Contributor,
    LanguageSource,
    DomainElement,
    UnitDomainElement,
    UnitValue,
    SentenceReference,
    Value,
    ValueSentence,
    ValueSetReference,
)
from crossgram.models import (
    Variety,
    LanguageReference,
    Construction,
    ContributionLanguage,
    Example,
    LParameter,
    LCode,
    LValueSet,
    CParameter,
    CCode,
    CValue,
    UnitReference,
    UnitSentence,
    UnitValueReference,
    UnitValueSentence,
    CrossgramDataSource,
)

MARTINS_FAVOURITE_ICONS = [
    'c0000dd',
    'cdd0000',
    'cffff00',
    'c009900',
    'c990099',
    's0000dd',
    'sdd0000',
    'sffff00',
    's009900',
    's990099',
    'cffffff',
    'c00ff00',
    'c00ffff',
    'ccccccc',
    'cff6600',
    'sffffff',
    's00ff00',
    's00ffff',
    'scccccc',
    'sff6600',
]

CODE_ICONS = MARTINS_FAVOURITE_ICONS[:]
CODE_ICONS.extend(
    icon
    for i in ORDERED_ICONS
    if (icon := getattr(i, 'name', i)) not in MARTINS_FAVOURITE_ICONS)


def parse_author(author_spec):
    if not isinstance(author_spec, dict):
        author_spec = {'name': author_spec}
    parsed_name = HumanName(author_spec.get('name', ''))
    author_id = slug('{}{}'.format(parsed_name.last, parsed_name.first))
    return author_id, author_spec, parsed_name


SourceTuple = namedtuple(
    'SourceTuple',
    ('bibkey', 'pages', 'source_string', 'source_pk'))


def parse_source(sources, source_string):
    match = re.fullmatch(r'([^[]+)(?:\[([^]]*)\])?', source_string)
    if match and match.group(1):
        bibkey, pages = match.groups()
        source = sources.get(bibkey)
        return SourceTuple(
            bibkey=bibkey,
            pages=pages or '',
            source_string=source_string,
            source_pk=source.pk if source else None)
    else:
        return None


def shorten_url(property_url):
    _, anchor = property_url.split('#')
    return anchor


def read_table(cldf, table):
    table = cldf.get(table)
    if not table:
        return

    column_map = {
        column.name: shorten_url(column.propertyUrl.uri)
        for column in table.tableSchema.columns
        if column.propertyUrl}
    for row in cldf[table]:
        yield {
            column_map.get(colname, colname): cell
            for colname, cell in row.items()}


class CLDFBenchSubmission:

    def __init__(self, cldf, sources, authors, title, readme):
        self.title = title
        self.cldf = cldf
        self.authors = authors
        self.sources = sources
        self.readme = readme

    def add_to_database(self, contribution, all_languages, all_contributors):
        # read cldf data

        cldf_constructions = list(read_table(self.cldf, 'constructions.csv'))
        cldf_lvalues = list(read_table(self.cldf, 'ValueTable'))
        cldf_cvalues = list(read_table(self.cldf, 'cvalues.csv'))
        cldf_examples = list(read_table(self.cldf, 'ExampleTable'))

        used_languages = {
            language_id
            for row in chain(cldf_lvalues, cldf_constructions, cldf_examples)
            if (language_id := row.get('languageReference'))}
        cldf_languages = [
            row
            for row in read_table(self.cldf, 'LanguageTable')
            if row['id'] in used_languages]

        if self.cldf.get('ParameterTable'):
            cldf_parameters = {
                cldf_parameter['id']: cldf_parameter
                for cldf_parameter in read_table(self.cldf, 'ParameterTable')}
        else:
            # Automatically build parameter table from value tables.
            cldf_parameters = {}
            for value in chain(cldf_lvalues, cldf_cvalues):
                parameter_id = value.get('parameterReference')
                if parameter_id and parameter_id not in cldf_parameters:
                    cldf_parameters[parameter_id] = {
                        'id': parameter_id,
                        'name': parameter_id,
                    }

        cldf_codes = {}
        for code_row in read_table(self.cldf, 'CodeTable'):
            param_id = code_row['parameterReference']
            if not param_id:
                continue
            if param_id not in cldf_codes:
                cldf_codes[param_id] = []
            cldf_codes[param_id].append(code_row)

        # Populate database

        contrib_langs = {}
        for cldf_language in cldf_languages:
            if (glottocode := cldf_language.get('glottocode')):
                lang_name = slug(cldf_language['name'])
                if glottocode not in contrib_langs:
                    contrib_langs[glottocode] = {}
                contrib_langs[glottocode][lang_name] = cldf_language['id']

        # try and deduplicate the languages based on their glottocode (and maybe
        # name)
        languages = {}
        for glottocode, by_name in contrib_langs.items():
            existing_langs = {}
            num = 1
            id_ = glottocode
            while id_ in all_languages:
                lang = all_languages[id_]
                existing_langs[slug(lang.name)] = lang
                num += 1
                id_ = '{}-{}'.format(glottocode, num)

            for name, old_id in by_name.items():
                if not existing_langs:
                    break
                elif len(existing_langs) == 1:
                    # this is the one!
                    languages[old_id] = list(existing_langs.values())[0]
                    break
                elif name in existing_langs:
                    # try and choose the language with the same name
                    languages[old_id] = existing_langs.pop(name)

        # FIXME: this is ugly
        new_ids = set()

        def _new_language_id(cldf_language):
            id_candidate = cldf_language['glottocode'] or cldf_language['id']
            number = 1
            new_id = id_candidate
            while new_id in all_languages or new_id in new_ids:
                number += 1
                new_id = '{}-{}'.format(id_candidate, number)
            new_ids.add(new_id)
            return new_id

        # TODO add glottocode, iso code, and wals code if available
        # TODO: add support for source_comment
        #  ^ complication: multiple contributions may add different source
        #  comments!
        new_langs_with_ids = [
            (cldf_language['id'], Variety(
                id=_new_language_id(cldf_language),
                name=cldf_language['name'],
                latitude=cldf_language['latitude'],
                longitude=cldf_language['longitude']))
            for cldf_language in cldf_languages
            if cldf_language['id'] not in languages]
        new_languages = [language for _, language in new_langs_with_ids]
        DBSession.add_all(new_languages)
        languages.update(new_langs_with_ids)

        lparameter_ids = {
            parameter_id
            for value in cldf_lvalues
            if (parameter_id := value.get('parameterReference'))}
        cparameter_ids = {
            parameter_id
            for value in cldf_cvalues
            if (parameter_id := value.get('parameterReference'))}
        lparameters = {
            cldf_parameter['id']: LParameter(
                id='{}-{}'.format(contribution.id, cldf_parameter['id']),
                contribution_pk=contribution.pk,
                name=cldf_parameter['name'],
                description=cldf_parameter['description'])
            for cldf_parameter in cldf_parameters.values()
            if cldf_parameter['id'] in lparameter_ids
            # consider parameters without values lparameters by default.
            or cldf_parameter['id'] not in cparameter_ids}
        cparameters = {
            cldf_parameter['id']: CParameter(
                id='{}-{}'.format(contribution.id, cldf_parameter['id']),
                contribution_pk=contribution.pk,
                name=cldf_parameter['name'],
                description=cldf_parameter['description'])
            for cldf_parameter in cldf_parameters.values()
            if cldf_parameter['id'] in cparameter_ids}
        DBSession.add_all(sorted(lparameters.values(), key=lambda p: p.id))
        DBSession.add_all(sorted(cparameters.values(), key=lambda p: p.id))

        parsed_authors = list(map(parse_author, self.authors))
        contributors = {
            author_id: all_contributors[author_id]
            for author_id, _, _ in parsed_authors
            if author_id in all_contributors}
        new_contributors = [
            Contributor(
                id=author_id,
                name=parsed_name.full_name,
                address=author_spec.get('affiliation'),
                url=author_spec.get('url'),
                email=author_spec.get('email'))
            for author_id, author_spec, parsed_name in parsed_authors
            if author_id not in contributors]
        DBSession.add_all(new_contributors)
        contributors.update(
            (contributor.id, contributor)
            for contributor in new_contributors)

        if self.sources:
            sources = [
                bibtex2source(bibrecord, CrossgramDataSource)
                for bibrecord in self.sources.records]
            sources = {
                bibrecord.id: bibrecord
                for bibrecord in sources}
            for source in sources.values():
                # give sources unique ids
                source.id = '{}-{}'.format(contribution.id, source.id)
                # add information bibtex2source doesn't know about
                source.contribution_pk = contribution.pk
            DBSession.add_all(sources.values())
        else:
            sources = {}

        DBSession.flush()

        DBSession.add_all(
            ContributionLanguage(
                language_pk=languages[cldf_language['id']].pk,
                contribution_pk=contribution.pk,
                custom_language_name=cldf_language['name'],
                source_comment=cldf_language.get('Source_comment'))
            for cldf_language in cldf_languages)

        DBSession.add_all(
            ContributionContributor(
                ord=ord,
                primary=spec.get('primary', True),
                contribution_pk=contribution.pk,
                contributor_pk=contributors[author_id].pk)
            for ord, (author_id, spec, _) in enumerate(parsed_authors, 1))

        DBSession.add_all(
            LanguageReference(
                key=st.bibkey,
                description=st.pages,
                language_pk=languages[cldf_language['id']].pk,
                source_pk=st.source_pk)
            for cldf_language in cldf_languages
            for source_string in sorted(set(cldf_language.get('source') or ()))
            if (st := parse_source(sources, source_string))
            and st.source_pk is not None)

        constructions = {
            cldf_construction['id']: Construction(
                id='{}-{}'.format(contribution.id, cldf_construction['id']),
                name=cldf_construction['name'],
                description=cldf_construction['description'],
                language_pk=languages[cldf_construction['languageReference']].pk,
                contribution_pk=contribution.pk,
                source_comment=cldf_construction.get('Source_comment'))
            for cldf_construction in cldf_constructions}
        DBSession.add_all(constructions.values())

        # add map icons to the codes
        code_icons = {}
        for param_id, param_codes in cldf_codes.items():
            param_icons = cycle(CODE_ICONS)
            for cldf_code in param_codes:
                code_icon = next(param_icons)
                if (custom_icon := cldf_code.get('Map_Icon')):
                    if re.fullmatch(r'[cstfd][0-9a-fA-F]{6}', custom_icon):
                        code_icon = custom_icon
                    else:
                        msg = "{}:Param {}:Code {}: invalid icon '{}'".format(
                            contribution.id, param_id, old_id, custom_icon)
                        print(msg, file=sys.stderr)
                code_icons[cldf_code['id']] = code_icon

        lcodes = {
            cldf_code['id']: LCode(
                id='{}-{}'.format(contribution.id, cldf_code['id']),
                parameter_pk=lparameter.pk,
                name=cldf_code['name'],
                description=cldf_code['description'],
                jsondata=dict(icon=code_icons[cldf_code['id']]))
            for parameter_id, param_codes in cldf_codes.items()
            for cldf_code in param_codes
            if (lparameter := lparameters.get(parameter_id))}
        ccodes = {
            cldf_code['id']: CCode(
                id='{}-{}'.format(contribution.id, cldf_code['id']),
                unitparameter_pk=cparameter.pk,
                name=cldf_code['name'],
                description=cldf_code['description'],
                jsondata=dict(icon=code_icons[cldf_code['id']]))
            for parameter_id, param_codes in cldf_codes.items()
            for cldf_code in param_codes
            if (cparameter := cparameters.get(parameter_id))}

        DBSession.add_all(lcodes.values())
        DBSession.add_all(ccodes.values())

        examples = {
            cldf_example['id']: Example(
                id='{}-{}'.format(contribution.number or contribution.id, ord),
                number=ord,
                name=cldf_example['primaryText'],
                description=cldf_example['translatedText'],
                analyzed='\t'.join(
                    (s or '') for s in cldf_example['analyzedWord']),
                gloss='\t'.join(
                    (s or '') for s in cldf_example['gloss']),
                comment=cldf_example['comment'],
                language_pk=languages[cldf_example['languageReference']].pk,
                contribution_pk=contribution.pk,
                source_comment=cldf_example.get('Source_comment'))
            for ord, cldf_example in enumerate(cldf_examples, 1)}
        DBSession.add_all(examples.values())

        DBSession.flush()

        DBSession.add_all(
            SentenceReference(
                key=st.bibkey,
                description=st.pages,
                sentence_pk=examples[cldf_example['id']].pk,
                source_pk=st.source_pk)
            for cldf_example in cldf_examples
            for source_string in sorted(set(cldf_example.get('source') or ()))
            if (st := parse_source(sources, source_string))
            and st.source_pk is not None)
        DBSession.add_all(
            UnitReference(
                key=st.bibkey,
                description=st.pages,
                unit_pk=constructions[cldf_construction['id']].pk,
                source_pk=st.source_pk)
            for cldf_construction in cldf_constructions
            for source_string in sorted(set(cldf_construction.get('source') or ()))
            if (st := parse_source(sources, source_string))
            and st.source_pk is not None)

        DBSession.add_all(
            UnitSentence(
                unit_pk=constructions[cldf_construction['id']].pk,
                sentence_pk=examples[example_id].pk)
            for cldf_construction in cldf_constructions
            for example_id in sorted(set(cldf_construction.get('exampleReference') or ())))

        lvaluesets = {}
        for cldf_value in cldf_lvalues:
            language_id = cldf_value['languageReference']
            parameter_id = cldf_value['parameterReference']
            if (language_id, parameter_id) not in lvaluesets:
                lvaluesets[language_id, parameter_id] = LValueSet(
                    id='{}-{}-{}'.format(
                        contribution.id, language_id, parameter_id),
                    language_pk=languages[language_id].pk,
                    parameter_pk=lparameters[parameter_id].pk,
                    contribution_pk=contribution.pk,
                    source_comment=cldf_value.get('Source_comment'))
        DBSession.add_all(lvaluesets.values())

        cvalues = {
            cldf_value['id']: CValue(
                id='{}-{}'.format(contribution.id, cldf_value['id']),
                unit_pk=constructions[cldf_value['Construction_ID']].pk,
                unitparameter_pk=cparameters[cldf_value['parameterReference']].pk,
                unitdomainelement=(code := ccodes.get(cldf_value['codeReference'])),
                name=code.name if code and code.name else cldf_value['value'],
                contribution_pk=contribution.pk,
                description=cldf_value.get('comment'),
                source_comment=cldf_value.get('Source_comment'))
            for cldf_value in cldf_cvalues}
        DBSession.add_all(cvalues.values())

        DBSession.flush()

        valueset_refs = OrderedDict()
        for cldf_value in cldf_lvalues:
            valueset = lvaluesets[
                cldf_value['languageReference'],
                cldf_value['parameterReference']]
            for source_string in sorted(set(cldf_value.get('source') or ())):
                st = parse_source(sources, source_string)
                if st and st.source_pk is not None:
                    # collect sources for all values in the same value set
                    if valueset.pk not in valueset_refs:
                        valueset_refs[valueset.pk] = set()
                    valueset_refs[valueset.pk].add(st)
        DBSession.add_all(
            ValueSetReference(
                key=st.bibkey,
                description=st.pages or None,
                valueset_pk=valueset_pk,
                source_pk=st.source_pk)
            for valueset_pk, st_set in valueset_refs.items()
            for st in sorted(st_set))

        DBSession.add_all(
            UnitValueSentence(
                unitvalue=cvalues[cldf_value['id']],
                sentence=examples[example_id])
            for cldf_value in cldf_cvalues
            for example_id in sorted(set(cldf_value.get('exampleReference') or ())))

        DBSession.add_all(
            UnitValueReference(
                key=st.bibkey,
                description=st.pages,
                unitvalue_pk=cvalues[cldf_value['id']].pk,
                source_pk=st.source_pk)
            for cldf_value in cldf_cvalues
            for source_string in sorted(set(cldf_value.get('source') or ()))
            if (st := parse_source(sources, source_string))
            and st.source_pk is not None)

        unique_constraint = set()
        lvalues = {}
        for cldf_value in cldf_lvalues:
            unique_fields = (
                cldf_value['languageReference'],
                cldf_value['parameterReference'],
                cldf_value['value'],
                cldf_value['codeReference'])
            # deal with a dataset violating a uniqueness constraint
            if unique_fields in unique_constraint:
                continue
            else:
                unique_constraint.add(unique_fields)
            valueset = lvaluesets[
                cldf_value['languageReference'],
                cldf_value['parameterReference']]
            code = lcodes.get(cldf_value['codeReference'])
            lvalues[cldf_value['id']] = Value(
                id='{}-{}'.format(contribution.id, cldf_value['id']),
                valueset_pk=valueset.pk,
                name=code.name if code and code.name else cldf_value['value'],
                domainelement_pk=code.pk if code else None,
                description=cldf_value.get('comment'))
        DBSession.add_all(lvalues.values())

        DBSession.flush()

        DBSession.add_all(
            ValueSentence(
                value_pk=lvalues[cldf_value['id']].pk,
                sentence_pk=examples[example_id].pk)
            for cldf_value in cldf_lvalues
            for example_id in sorted(set(cldf_value.get('exampleReference') or ()))
            if cldf_value['id'] in lvalues)

        return new_languages, new_contributors

    @classmethod
    def load(cls, path, contrib_md):
        # zenodo download dumps all files into a subfolder
        if not (path / 'cldf').exists():
            for subpath in path.glob('*'):
                if (subpath / 'cldf').exists():
                    path = subpath
                    break
        assert path.exists(), str(path)

        try:
            cldf_dataset = next(
                dataset
                for dataset in iter_datasets(path / 'cldf')
                if dataset.module == 'StructureDataset')
        except StopIteration:
            raise ValueError('No cldf metadata file found in {}'.format(path))

        bib_path = path / 'cldf' / 'sources.bib'
        sources = bibtex.Database.from_file(bib_path) if bib_path.exists() else None

        md_path = path / 'metadata.json'
        md = jsonlib.load(md_path) if md_path.exists() else {}

        # XXX maybe also allow README.txt?
        readme_path = path / 'README.md'
        try:
            with readme_path.open(encoding='utf-8') as f:
                readme = f.read().strip()
        except IOError:
            readme = None

        authors = contrib_md.get('authors') or ()

        return cls(cldf_dataset, sources, authors, md.get('title'), readme)
