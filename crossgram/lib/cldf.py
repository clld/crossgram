import re
import sys
from collections import namedtuple
from itertools import chain, cycle

import clld.db.models as common
from clld.cliutil import bibtex2source
from clld.db.meta import DBSession
from clld.lib import bibtex
from clld.web.icon import ORDERED_ICONS
from clldutils import jsonlib
from clldutils.misc import slug
from nameparser import HumanName
from pycldf import iter_datasets

from crossgram import models


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
    author_id = slug(f'{parsed_name.last}{parsed_name.first}')
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


def cldf_parameters_from_values(cldf_lvalues, cldf_cvalues):
    cldf_parameters = []
    parameter_ids = set()
    for value in chain(cldf_lvalues, cldf_cvalues):
        parameter_id = value.get('parameterReference')
        if parameter_id and parameter_id not in parameter_ids:
            parameter_ids.add(parameter_id)
            cldf_parameters.append({
                'id': parameter_id,
                'name': parameter_id,
            })
    return cldf_parameters


def make_cldf_codes(csv_rows):
    cldf_codes = {}
    for code_row in csv_rows:
        param_id = code_row['parameterReference']
        if not param_id:
            continue
        if param_id not in cldf_codes:
            cldf_codes[param_id] = []
        cldf_codes[param_id].append(code_row)
    return cldf_codes


def languages_for_contribution(cldf_languages):
    contrib_langs = {}
    for cldf_language in cldf_languages:
        if (glottocode := cldf_language.get('glottocode')):
            lang_name = slug(cldf_language['name'])
            if glottocode not in contrib_langs:
                contrib_langs[glottocode] = {}
            contrib_langs[glottocode][lang_name] = cldf_language['id']
    return contrib_langs


def make_cparameters(cldf_parameters, cldf_cvalues, contribution):
    cparameter_ids = {
        parameter_id
        for value in cldf_cvalues
        if (parameter_id := value.get('parameterReference'))}
    return {
        cldf_parameter['id']: models.CParameter(
            id='{}-{}'.format(contribution.id, cldf_parameter['id']),
            contribution_pk=contribution.pk,
            name=cldf_parameter['name'],
            description=cldf_parameter['description'])
        for cldf_parameter in cldf_parameters
        if cldf_parameter['id'] in cparameter_ids}


def make_lparameters(
    cldf_parameters, cldf_lvalues, contribution, cparameter_ids
):
    lparameter_ids = {
        parameter_id
        for value in cldf_lvalues
        if (parameter_id := value.get('parameterReference'))}
    return {
        cldf_parameter['id']: models.LParameter(
            id='{}-{}'.format(contribution.id, cldf_parameter['id']),
            contribution_pk=contribution.pk,
            name=cldf_parameter['name'],
            description=cldf_parameter['description'])
        for cldf_parameter in cldf_parameters
        if cldf_parameter['id'] in lparameter_ids
        # consider parameters without values lparameters by default.
        or cldf_parameter['id'] not in cparameter_ids}


def only_existing_contributors(parsed_names, all_contributors):
    return {
        author_id: all_contributors[author_id]
        for author_id, _, _ in parsed_names
        if author_id in all_contributors}


def only_nonexisting_contributors(parsed_names, duplicate_contributors):
    return {
        author_id: common.Contributor(
            id=author_id,
            name=parsed_name.full_name,
            address=author_spec.get('affiliation'),
            url=author_spec.get('url'),
            email=author_spec.get('email'))
        for author_id, author_spec, parsed_name in parsed_names
        if author_id not in duplicate_contributors}


def only_existing_languages(contribution_languages, all_languages):
    # try and deduplicate the languages based on their glottocode (and maybe
    # name)
    languages = {}
    for glottocode, by_name in contribution_languages.items():
        existing_langs = {}
        num = 1
        id_ = glottocode
        while id_ in all_languages:
            lang = all_languages[id_]
            existing_langs[slug(lang.name)] = lang
            num += 1
            id_ = f'{glottocode}-{num}'

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
    return languages


def only_nonexisting_languages(
    cldf_languages, duplicate_languages, all_languages
):
    # FIXME: this is ugly
    new_ids = set()

    def _new_language_id(cldf_language):
        id_candidate = cldf_language['glottocode'] or cldf_language['id']
        number = 1
        new_id = id_candidate
        while new_id in all_languages or new_id in new_ids:
            number += 1
            new_id = f'{id_candidate}-{number}'
        new_ids.add(new_id)
        return new_id

    # TODO add glottocode, iso code, and wals code if available
    # TODO: add support for source_comment
    #  ^ complication: multiple contributions may add different source
    #  comments!
    return {
        cldf_language['id']: models.Variety(
            id=_new_language_id(cldf_language),
            name=cldf_language['name'],
            latitude=cldf_language['latitude'],
            longitude=cldf_language['longitude'])
        for cldf_language in cldf_languages
        if cldf_language['id'] not in duplicate_languages}


def make_sources(records, contribution):
    sources = {
        bibrecord.id: bibtex2source(bibrecord, models.CrossgramDataSource)
        for bibrecord in records}
    for source in sources.values():
        # give sources unique ids
        source.id = f'{contribution.id}-{source.id}'
        # add information bibtex2source doesn't know about
        source.contribution_pk = contribution.pk
    return sources


def iter_contribution_languages(cldf_languages, languages, contribution):
    return (
        models.ContributionLanguage(
            language_pk=languages[cldf_language['id']].pk,
            contribution_pk=contribution.pk,
            custom_language_name=cldf_language['name'],
            source_comment=cldf_language.get('Source_comment'))
        for cldf_language in cldf_languages)


def iter_contribution_contributors(parsed_names, contributors, contribution):
    return (
        common.ContributionContributor(
            ord=ord,
            primary=spec.get('primary', True),
            contribution_pk=contribution.pk,
            contributor_pk=contributors[author_id].pk)
        for ord, (author_id, spec, _) in enumerate(parsed_names, 1))


def iter_language_sources(cldf_languages, languages, sources):
    return (
        models.LanguageReference(
            key=source_tuple.bibkey,
            description=source_tuple.pages,
            language_pk=languages[cldf_language['id']].pk,
            source_pk=source_tuple.source_pk)
        for cldf_language in cldf_languages
        for source_string in sorted(set(cldf_language.get('source') or ()))
        if (source_tuple := parse_source(sources, source_string))
        and source_tuple.source_pk is not None)


def _db_param(parameter_id, topic_pk, lparameters, cparameters):
    if (cparam := cparameters.get(parameter_id)):
        return models.UnitParameterTopic(
            unitparameter_pk=cparam.pk,
            topic_pk=topic_pk)
    else:
        return models.ParameterTopic(
            parameter_pk=lparameters[parameter_id].pk,
            topic_pk=topic_pk)


def iter_parameter_topics(cldf_parameters, lparameters, cparameters, topics):
    return (
        _db_param(cldf_parameter['id'], topic.pk, lparameters, cparameters)
        for cldf_parameter in cldf_parameters
        for grammacode in cldf_parameter.get('Grammacodes', ())
        if (topic := topics.get(grammacode)))


def make_constructions(cldf_constructions, languages, contribution):
    return {
        cldf_construction['id']: models.Construction(
            id='{}-{}'.format(contribution.id, cldf_construction['id']),
            name=cldf_construction['name'],
            description=cldf_construction['description'],
            language_pk=languages[cldf_construction['languageReference']].pk,
            contribution_pk=contribution.pk,
            source_comment=cldf_construction.get('Source_comment'))
        for cldf_construction in cldf_constructions}


def assign_icons_to_codes(cldf_codes, contribution):
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
                        contribution.id,
                        param_id,
                        cldf_code['id'],
                        custom_icon)
                    print(msg, file=sys.stderr)
            code_icons[cldf_code['id']] = code_icon
    return code_icons


def make_lcodes(cldf_codes, lparameters, code_icons, contribution):
    return {
        cldf_code['id']: models.LCode(
            id='{}-{}'.format(contribution.id, cldf_code['id']),
            parameter_pk=lparameter.pk,
            name=cldf_code['name'],
            description=cldf_code['description'],
            jsondata={'icon': code_icons[cldf_code['id']]})
        for parameter_id, param_codes in cldf_codes.items()
        for cldf_code in param_codes
        if (lparameter := lparameters.get(parameter_id))}


def make_ccodes(cldf_codes, cparameters, code_icons, contribution):
    return {
        cldf_code['id']: models.CCode(
            id='{}-{}'.format(contribution.id, cldf_code['id']),
            unitparameter_pk=cparameter.pk,
            name=cldf_code['name'],
            description=cldf_code['description'],
            jsondata={'icon': code_icons[cldf_code['id']]})
        for parameter_id, param_codes in cldf_codes.items()
        for cldf_code in param_codes
        if (cparameter := cparameters.get(parameter_id))}


def make_examples(cldf_examples, languages, contribution):
    return {
        cldf_example['id']: models.Example(
            id=f'{contribution.number or contribution.id}-{ord}',
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


def iter_example_sources(cldf_examples, examples, sources):
    return (
        common.SentenceReference(
            key=source_tuple.bibkey,
            description=source_tuple.pages,
            sentence_pk=examples[cldf_example['id']].pk,
            source_pk=source_tuple.source_pk)
        for cldf_example in cldf_examples
        for source_string in sorted(set(cldf_example.get('source') or ()))
        if (source_tuple := parse_source(sources, source_string))
        and source_tuple.source_pk is not None)


def iter_construction_sources(cldf_constructions, constructions, sources):
    return (
        models.UnitReference(
            key=source_tuple.bibkey,
            description=source_tuple.pages,
            unit_pk=constructions[cldf_construction['id']].pk,
            source_pk=source_tuple.source_pk)
        for cldf_construction in cldf_constructions
        for source_string in sorted(set(cldf_construction.get('source') or ()))
        if (source_tuple := parse_source(sources, source_string))
        and source_tuple.source_pk is not None)


def iter_construction_examples(cldf_constructions, constructions, examples):
    return (
        models.UnitSentence(
            unit_pk=constructions[cldf_construction['id']].pk,
            sentence_pk=examples[example_id].pk)
        for cldf_construction in cldf_constructions
        for example_id in sorted(
            set(cldf_construction.get('exampleReference') or ())))


def make_cvalues(
    cldf_cvalues, constructions, cparameters, ccodes, contribution
):
    return {
        cldf_value['id']: models.CValue(
            id='{}-{}'.format(contribution.id, cldf_value['id']),
            unit_pk=constructions[cldf_value['Construction_ID']].pk,
            unitparameter_pk=cparameters[cldf_value['parameterReference']].pk,
            unitdomainelement=(code := ccodes.get(cldf_value['codeReference'])),
            name=code.name if code and code.name else cldf_value['value'],
            contribution_pk=contribution.pk,
            description=cldf_value.get('comment'),
            source_comment=cldf_value.get('Source_comment'))
        for cldf_value in cldf_cvalues}


def make_lvaluesets(cldf_lvalues, languages, lparameters, contribution):
    lvaluesets = {}
    for cldf_value in cldf_lvalues:
        language_id = cldf_value['languageReference']
        parameter_id = cldf_value['parameterReference']
        if (language_id, parameter_id) not in lvaluesets:
            lvaluesets[language_id, parameter_id] = models.LValueSet(
                id=f'{contribution.id}-{language_id}-{parameter_id}',
                language_pk=languages[language_id].pk,
                parameter_pk=lparameters[parameter_id].pk,
                contribution_pk=contribution.pk,
                source_comment=cldf_value.get('Source_comment'))
    return lvaluesets


def iter_value_sources(cldf_lvalues, lvaluesets, sources):
    valueset_refs = {}
    for cldf_value in cldf_lvalues:
        valueset = lvaluesets[
            cldf_value['languageReference'],
            cldf_value['parameterReference']]
        for source_string in sorted(set(cldf_value.get('source') or ())):
            source_tuple = parse_source(sources, source_string)
            if source_tuple and source_tuple.source_pk is not None:
                # collect sources for all values in the same value set
                if valueset.pk not in valueset_refs:
                    valueset_refs[valueset.pk] = set()
                valueset_refs[valueset.pk].add(source_tuple)
    return (
        common.ValueSetReference(
            key=source_tuple.bibkey,
            description=source_tuple.pages or None,
            valueset_pk=valueset_pk,
            source_pk=source_tuple.source_pk)
        for valueset_pk, st_set in valueset_refs.items()
        for source_tuple in sorted(st_set))


def iter_cvalue_examples(cldf_cvalues, cvalues, examples):
    return (
        models.UnitValueSentence(
            unitvalue=cvalues[cldf_value['id']],
            sentence=examples[example_id])
        for cldf_value in cldf_cvalues
        for example_id in sorted(set(cldf_value.get('exampleReference') or ())))


def iter_cvalue_sources(cldf_cvalues, cvalues, sources):
    return (
        models.UnitValueReference(
            key=source_tuple.bibkey,
            description=source_tuple.pages,
            unitvalue_pk=cvalues[cldf_value['id']].pk,
            source_pk=source_tuple.source_pk)
        for cldf_value in cldf_cvalues
        for source_string in sorted(set(cldf_value.get('source') or ()))
        if (source_tuple := parse_source(sources, source_string))
        and source_tuple.source_pk is not None)


def make_lvalues(cldf_lvalues, lvaluesets, lcodes, contribution):
    lvalues = {}
    unique_constraint = set()
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
        lvalues[cldf_value['id']] = common.Value(
            id='{}-{}'.format(contribution.id, cldf_value['id']),
            valueset_pk=valueset.pk,
            name=code.name if code and code.name else cldf_value['value'],
            domainelement_pk=code.pk if code else None,
            description=cldf_value.get('comment'))
    return lvalues


def iter_value_examples(cldf_lvalues, lvalues, examples):
    return (
        common.ValueSentence(
            value_pk=lvalues[cldf_value['id']].pk,
            sentence_pk=examples[example_id].pk)
        for cldf_value in cldf_lvalues
        for example_id in sorted(set(cldf_value.get('exampleReference') or ()))
        if cldf_value['id'] in lvalues)


class CLDFBenchSubmission:

    def __init__(self, cldf, sources, authors, title, readme):
        self.title = title
        self.cldf = cldf
        self.authors = authors
        self.sources = sources
        self.readme = readme

    def add_to_database(
        self, contribution, all_languages, all_contributors, topics
    ):
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
            cldf_parameters = list(read_table(self.cldf, 'ParameterTable'))
        else:
            # Automatically build parameter table from value tables.
            cldf_parameters = cldf_parameters_from_values(
                cldf_lvalues, cldf_cvalues)

        cldf_codes = make_cldf_codes(read_table(self.cldf, 'CodeTable'))

        # Populate database

        contrib_langs = languages_for_contribution(cldf_languages)
        languages = only_existing_languages(contrib_langs, all_languages)
        added_languages = only_nonexisting_languages(
            cldf_languages, languages, all_languages)
        languages.update(added_languages.items())
        DBSession.add_all(added_languages.values())

        cparameters = make_cparameters(
            cldf_parameters, cldf_cvalues, contribution)
        lparameters = make_lparameters(
            cldf_parameters, cldf_lvalues, contribution, cparameters)
        DBSession.add_all(cparameters.values())
        DBSession.add_all(lparameters.values())

        parsed_names = list(map(parse_author, self.authors))
        contributors = only_existing_contributors(
            parsed_names, all_contributors)
        added_contributors = only_nonexisting_contributors(
            parsed_names, contributors)
        contributors.update(added_contributors.items())
        DBSession.add_all(added_contributors.values())

        if self.sources:
            sources = make_sources(self.sources.records, contribution)
            DBSession.add_all(sources.values())
        else:
            sources = {}

        DBSession.flush()

        DBSession.add_all(iter_contribution_languages(
            cldf_languages, languages, contribution))
        DBSession.add_all(iter_contribution_contributors(
            parsed_names, contributors, contribution))
        DBSession.add_all(iter_language_sources(
            cldf_languages, languages, sources))
        DBSession.add_all(iter_parameter_topics(
            cldf_parameters, lparameters, cparameters, topics))

        constructions = make_constructions(
            cldf_constructions, languages, contribution)
        DBSession.add_all(constructions.values())

        code_icons = assign_icons_to_codes(cldf_codes, contribution)
        lcodes = make_lcodes(cldf_codes, lparameters, code_icons, contribution)
        ccodes = make_ccodes(cldf_codes, cparameters, code_icons, contribution)
        DBSession.add_all(lcodes.values())
        DBSession.add_all(ccodes.values())

        examples = make_examples(cldf_examples, languages, contribution)
        DBSession.add_all(examples.values())

        DBSession.flush()

        DBSession.add_all(iter_example_sources(
            cldf_examples, examples, sources))
        DBSession.add_all(iter_construction_sources(
            cldf_constructions, constructions, sources))
        DBSession.add_all(iter_construction_examples(
            cldf_constructions, constructions, examples))

        cvalues = make_cvalues(
            cldf_cvalues, constructions, cparameters, ccodes, contribution)
        DBSession.add_all(cvalues.values())

        lvaluesets = make_lvaluesets(
            cldf_lvalues, languages, lparameters, contribution)
        DBSession.add_all(lvaluesets.values())

        DBSession.flush()

        DBSession.add_all(iter_value_sources(cldf_lvalues, lvaluesets, sources))
        DBSession.add_all(iter_cvalue_examples(cldf_cvalues, cvalues, examples))
        DBSession.add_all(iter_cvalue_sources(cldf_cvalues, cvalues, sources))

        lvalues = make_lvalues(cldf_lvalues, lvaluesets, lcodes, contribution)
        DBSession.add_all(lvalues.values())

        DBSession.flush()

        DBSession.add_all(iter_value_examples(cldf_lvalues, lvalues, examples))

        return added_languages.values(), added_contributors.values()

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
            raise ValueError(f'No cldf metadata file found in {path}')

        bib_path = path / 'cldf' / 'sources.bib'
        sources = bibtex.Database.from_file(bib_path, lowercase=True) if bib_path.exists() else None

        md_path = path / 'metadata.json'
        metadata = jsonlib.load(md_path) if md_path.exists() else {}

        # XXX maybe also allow README.txt?
        readme_path = path / 'README.md'
        try:
            with readme_path.open(encoding='utf-8') as f:
                readme = f.read().strip()
        except IOError:
            readme = None

        authors = contrib_md.get('authors') or ()

        return cls(
            cldf_dataset, sources, authors, metadata.get('title'), readme)
