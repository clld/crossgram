from datetime import date
import pathlib
import re

from clld.scripts.util import Data, bibtex2source
from clld.lib import bibtex
from clldutils import jsonlib
from clldutils.misc import slug
from nameparser import HumanName
from pycldf.dataset import StructureDataset

from clld.db.meta import DBSession
from clld.db.models import (
    ContributionContributor,
    Contributor,
    DomainElement,
    Language,
    UnitDomainElement,
    UnitValue,
    SentenceReference,
    Value,
    ValueSentence,
    ValueSet,
    ValueSetReference,
)
from crossgram.models import (
    CrossgramData,
    Construction,
    Example,
    LParameter,
    CParameter,
    UnitValueSentence,
    UnitValueReference,
    CrossgramDataSource,
)


CONSTR_MAP = {
    'Name': 'name',
    'Description': 'description'}

LANG_MAP = {
    'Name': 'name',
    'Latitude': 'latitude',
    'Longitude': 'longitude'}

PARAM_MAP = {
    'Name': 'name',
    'Description': 'description'}

LCODE_MAP = {
    'Name': 'name',
    'Description': 'description',
    'Number': 'number'}

CCODE_MAP = {
    'Name': 'name',
    'Description': 'description',
    'Number': 'ord'}

EXAMPLE_MAP = {
    'Primary_Text': 'name',
    'Translated_Text': 'description',
    'Analyzed_Word': 'analyzed',
    'Gloss': 'gloss',
    'Source': 'source'}


def map_cols(mapping, col):
    return {
        new: col[old]
        for old, new in mapping.items()
        if old in col}


def _merge_field(pair):
    k, v = pair
    if k in ('Analyzed_Word', 'Gloss', 'Source'):
        return k, '\t'.join(v)
    return k, v


def _merge_glosses(col):
    return dict(map(_merge_field, col.items()))


class CLDFBenchSubmission:

    def __init__(self, sid, number, published, cldf, md, authors, sources):
        self.sid = sid
        self.number = number
        self.published = published
        self.md = md
        self.cldf = cldf
        self.authors = authors
        self.sources = sources

    def add_to_database(self, data, language_id_map):
        contrib = data.add(
            CrossgramData,
            self.sid,
            id=self.sid,
            number=self.number,
            published=self.published,
            name=self.md.get('title'),
            description=self.md.get('description'))

        for language_row in self.cldf['LanguageTable']:
            old_id = language_row.get('ID')
            if not old_id:
                continue

            # Apparently some datasets contain multiple languages sharing the
            # same Glottocode...  So try and use the name to distinguish them
            id_candidate = language_row.get('Glottocode') or old_id
            number = 1
            new_id = id_candidate
            lang = data['Language'].get(new_id)
            while lang and slug(lang.name) != slug(language_row.get('Name')):
                number += 1
                new_id = '{}-{}'.format(id_candidate, number)
                lang = data['Language'].get(new_id)

            language_id_map[old_id] = new_id
            if not lang:
                data.add(
                    Language,
                    new_id,
                    id=new_id,
                    **map_cols(LANG_MAP, language_row))

        DBSession.flush()

        for i, spec in enumerate(self.authors):
            if not isinstance(spec, dict):
                spec = {'name': spec}
            name = spec.get('name', '')
            parsed_name = HumanName(name)
            author_id = slug('{}{}'.format(parsed_name.last, parsed_name.first))
            author = data['Contributor'].get(author_id)
            if not author:
                author = data.add(
                    Contributor,
                    author_id,
                    id=author_id,
                    name=name,
                    address=spec.get('affiliation'),
                    url=spec.get('url'),
                    email=spec.get('email'))
                DBSession.flush()
            DBSession.add(ContributionContributor(
                ord=i + 1,
                primary=spec.get('primary', True),
                contribution=contrib,
                contributor=author))

        biblio_map = {}
        if self.sources:
            for bibrecord in self.sources.records:
                source = bibtex2source(bibrecord, CrossgramDataSource)
                old_id = bibrecord.id
                new_id = '{}-{}'.format(contrib.id, old_id)
                source.id = new_id
                source.contribution = contrib
                biblio_map[old_id] = source

        for constr_row in self.cldf.get('constructions.csv', ()):
            old_id = constr_row.get('ID')
            if not old_id:
                continue
            new_id = '{}-{}'.format(contrib.id, old_id)
            lang_new_id = language_id_map.get(constr_row['Language_ID'])
            lang = data['Language'].get(lang_new_id)
            data.add(
                Construction,
                old_id,
                language=lang,
                contribution=contrib,
                id=new_id,
                **map_cols(CONSTR_MAP, constr_row))

        cparam_ids = {
            row['Parameter_ID']
            for row in self.cldf.get('cvalues.csv', ())
            if 'Parameter_ID' in row}

        for param_row in self.cldf.get('ParameterTable', ()):
            old_id = param_row.get('ID')
            if not old_id:
                continue
            new_id = '{}-{}'.format(contrib.id, old_id)
            data.add(
                CParameter if old_id in cparam_ids else LParameter,
                old_id,
                contribution=contrib,
                id=new_id,
                **map_cols(PARAM_MAP, param_row))

        DBSession.flush()

        for code_row in self.cldf.get('CodeTable', ()):
            old_id = code_row.get('ID')
            param_id = code_row.get('Parameter_ID')
            if not old_id or not param_id:
                continue
            new_id = '{}-{}'.format(contrib.id, old_id)
            if param_id in cparam_ids:
                param = data['CParameter'].get(param_id)
                data.add(
                    UnitDomainElement,
                    old_id,
                    parameter=param,
                    id=new_id,
                    **map_cols(CCODE_MAP, code_row))
            else:
                param = data['LParameter'].get(param_id)
                data.add(
                    DomainElement,
                    old_id,
                    parameter=param,
                    id=new_id,
                    **map_cols(LCODE_MAP, code_row))

        for example_row in self.cldf.get('ExampleTable', ()):
            old_id = example_row.get('ID')
            lang_new_id = language_id_map.get(example_row['Language_ID'])
            lang = data['Language'].get(lang_new_id)
            if not old_id or not lang:
                continue
            new_id = '{}-{}'.format(contrib.id, old_id)
            example_row = _merge_glosses(example_row)
            example = data.add(
                Example,
                old_id,
                language=lang,
                contribution=contrib,
                id=new_id,
                **map_cols(EXAMPLE_MAP, example_row))

            DBSession.flush()
            # FIXME does not work
            #  Idea 1: mabe Source is not an array here?
            source_string = example_row.get('Source')
            if source_string:
                match = re.fullmatch(r'([^[]+)(\[[^]]*\])?', source_string)
                if not match or not match.group(1):
                    continue
                source = biblio_map.get(match.group(1))
                if source:
                    DBSession.add(SentenceReference(
                            sentence_pk=example.pk,
                            source_pk=source.pk))

        DBSession.flush()

        for value_row in self.cldf.get('ValueTable', ()):
            old_id = value_row.get('ID')
            lang_new_id = language_id_map.get(value_row['Language_ID'])
            lang = data['Language'].get(lang_new_id)
            param = data['LParameter'].get(value_row['Parameter_ID'])
            code = data['DomainElement'].get(value_row['Code_ID'])
            if not old_id or not lang or not param or not code:
                continue
            new_id = '{}-{}'.format(contrib.id, old_id)
            name = code.name
            source = ';'.join(value_row['Source']) if 'Source' in value_row else None

            valueset = data['ValueSet'].get((lang.pk, param.pk))
            if not valueset:
                valueset = data.add(
                    ValueSet, (lang.pk, param.pk), id=new_id, language=lang,
                    parameter=param, contribution=contrib, source=source)

            DBSession.flush()
            value = data.add(
                Value, old_id,
                id=new_id, name=name, valueset=valueset, domainelement=code)

            for source_string in sorted(set(value_row.get('Source') or ())):
                match = re.fullmatch(r'([^[]+)(\[[^]]*\])?', source_string)
                if not match or not match.group(1):
                    continue
                source = biblio_map.get(match.group(1))
                if source:
                    DBSession.add(ValueSetReference(
                        valueset=valueset, source_pk=source.pk))

            DBSession.flush()
            for ex_id in set(value_row.get('Example_IDs', ())):
                example = data['Example'].get(ex_id)
                if example:
                    DBSession.add(ValueSentence(value=value, sentence=example))

        for cvalue_row in self.cldf.get('cvalues.csv', ()):
            old_id = cvalue_row.get('ID')
            constr = data['Construction'].get(cvalue_row['Construction_ID'])
            param = data['CParameter'].get(cvalue_row['Parameter_ID'])
            code = data['UnitDomainElement'].get(cvalue_row['Code_ID'])
            if not old_id or not constr or not param or not code:
                continue
            new_id = '{}-{}'.format(contrib.id, old_id)
            name = code.name
            # TODO add source (not valid in UnitValue itself -- maybe make UnitValueSource table?)
            source = ';'.join(value_row['Source']) if 'Source' in value_row else None

            cvalue = data.add(
                UnitValue, old_id,
                id=new_id, name=name, contribution=contrib, unit=constr,
                unitparameter=param, unitdomainelement=code)

            DBSession.flush()
            for ex_id in sorted(set(cvalue_row.get('Example_IDs') or ())):
                example = data['Example'].get(ex_id)
                if example:
                    DBSession.add(UnitValueSentence(
                        unitvalue=cvalue, sentence=example))

            for source_string in sorted(set(cvalue_row.get('Source') or ())):
                match = re.fullmatch(r'([^[]+)(\[[^]]*\])?', source_string)
                if not match or not match.group(1):
                    continue
                source = biblio_map.get(match.group(1))
                if source:
                    DBSession.add(UnitValueReference(
                        unitvalue=cvalue, source_pk=source.pk))

    @classmethod
    def load(cls, contrib_md):
        repo_path = pathlib.Path(contrib_md.get('repo'))
        assert repo_path.exists()
        cldf_path = repo_path / 'cldf' / 'StructureDataset-metadata.json'
        md_path = repo_path / 'metadata.json'
        config_path = repo_path / 'etc' / 'config.json'
        bib_path = repo_path / 'cldf' / 'sources.bib'

        md = jsonlib.load(md_path) if md_path.exists() else {}

        config = jsonlib.load(config_path) if config_path.exists() else {}
        authors = contrib_md.get('authors') or config.get('authors') or ()

        cldf_dataset = StructureDataset.from_metadata(cldf_path)
        sources = bibtex.Database.from_file(bib_path) if bib_path.exists() else None

        submission_id = (
            contrib_md.get('id')
            or md.get('id')
            or cldf_dataset.properties.get('rc:ID')
            or slug(path.name))
        number = int(contrib_md['number'])
        published = date.fromisoformat(contrib_md['published'])
        return cls(
            submission_id, number, published, cldf_dataset, md, authors,
            sources)
