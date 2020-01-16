from clld.scripts.util import Data
from clldutils import jsonlib
from clldutils.misc import slug
from nameparser import HumanName
from pycldf.dataset import StructureDataset

from clld.db.meta import DBSession
from clld.db.models import (
    Contribution,
    ContributionContributor,
    Contributor,
    DomainElement,
    Language,
    Parameter,
    Sentence,
    Value,
    ValueSentence,
    ValueSet,
    Unit,
    UnitDomainElement,
    UnitParameter,
    UnitValue,
)
from crossgram.models import (
    DataSetContrib,
    UnitValueSentence,
)


CONSTR_MAP = {
    'ID': 'id',
    'Name': 'name',
    'Description': 'description'}

LANG_MAP = {
    'ID': 'id',
    'Name': 'name',
    'Latitude': 'latitude',
    'Longitude': 'longitude'}

PARAM_MAP = {
    'ID': 'id',
    'Name': 'name',
    'Description': 'description'}

LCODE_MAP = {
    'ID': 'id',
    'Name': 'name',
    'Description': 'description',
    'Number': 'number'}

CCODE_MAP = {
    'ID': 'id',
    'Name': 'name',
    'Description': 'description',
    'Number': 'ord'}

EXAMPLE_MAP = {
    'ID': 'id',
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


def load_cldfbench(path):
    assert path.exists()
    cldf_path = path / 'cldf' / 'StructureDataset-metadata.json'
    md_path = path / 'metadata.json'
    config_path = path / 'etc' / 'config.json'

    md = jsonlib.load(md_path) if md_path.exists() else {}

    config = jsonlib.load(config_path) if config_path.exists() else {}
    authors = config.get('authors', ())

    cldf_dataset = StructureDataset.from_metadata(cldf_path)

    submission_id = (
        md.get('id')
        or cldf_dataset.properties.get('rc:ID')
        or path.name)
    return CLDFBenchSubmission(submission_id, cldf_dataset, md, authors)


class CLDFBenchSubmission:

    def __init__(self, sid, cldf, md, authors):
        self.sid = sid
        self.md = md
        self.cldf = cldf
        self.authors = authors

    def load(self, data=None):
        data = data or Data()
        contrib = data.add(
            DataSetContrib,
            self.sid,
            id=self.sid,
            name=self.md.get('title'),
            description=self.md.get('description'))

        for language_row in self.cldf['LanguageTable']:
            # TODO language ids should be glottocodes
            id_ = language_row['ID']
            if id_ not in data['Language']:
                data.add(Language, id_, **map_cols(LANG_MAP, language_row))

        cparam_ids = {
            row['Parameter_ID']
            for row in self.cldf['cvalues.csv']
            if 'Parameter_ID' in row}

        for param_row in self.cldf['ParameterTable']:
            id_ = param_row['ID']
            data.add(
                UnitParameter if id_ in cparam_ids else Parameter,
                id_,
                **map_cols(PARAM_MAP, param_row))

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
            ContributionContributor(
                ord=i + 1,
                primary=spec.get('primary', True),
                contribution=contrib,
                contributor=author)

        for constr_row in self.cldf['constructions.csv']:
            # TODO proper constr id
            id_ = constr_row['ID']
            lang = data['Language'].get(constr_row['Language_ID'])
            data.add(
                Unit,
                id_,
                language=lang,
                **map_cols(CONSTR_MAP, constr_row))

        # TODO Check for missing/invalid refs

        for code_row in self.cldf['CodeTable']:
            id_ = code_row.get('ID')
            param_id = code_row['Parameter_ID']
            if param_id in cparam_ids:
                param = data['UnitParameter'].get(param_id)
                data.add(
                    UnitDomainElement,
                    id_,
                    parameter=param,
                    **map_cols(CCODE_MAP, code_row))
            else:
                param = data['Parameter'].get(param_id)
                data.add(
                    DomainElement,
                    id_,
                    parameter=param,
                    **map_cols(LCODE_MAP, code_row))

        for example_row in self.cldf['ExampleTable']:
            id_ = example_row.get('ID')
            lang = data['Language'].get(example_row['Language_ID'])
            example_row = _merge_glosses(example_row)
            data.add(
                Sentence,
                id_,
                language=lang,
                **map_cols(EXAMPLE_MAP, example_row))

        DBSession.flush()

        for value_row in self.cldf['ValueTable']:
            id_ = value_row.get('ID')
            lang = data['Language'].get(value_row['Language_ID'])
            param = data['Parameter'].get(value_row['Parameter_ID'])
            code = data['DomainElement'].get(value_row['Code_ID'])
            if not lang or not param or not code:
                # TODO warn about this
                continue
            name = code.name
            source = ';'.join(value_row['Source']) if 'Source' in value_row else None

            valueset = data['ValueSet'].get((lang.pk, param.pk))
            if not valueset:
                valueset = data.add(
                    ValueSet, (lang.pk, param.pk), id=id_, language=lang,
                    parameter=param, contribution=contrib, source=source)

            DBSession.flush()
            value = data.add(
                Value, id_,
                id=id_, name=name, valueset=valueset, domainelement=code)

            DBSession.flush()
            for ex_id in set(value_row.get('Example_IDs', ())):
                example = data['Sentence'].get(ex_id)
                if example:
                    ValueSentence(value=value, sentence=example)

        for cvalue_row in self.cldf['cvalues.csv']:
            id_ = cvalue_row.get('ID')
            constr = data['Unit'].get(cvalue_row['Construction_ID'])
            param = data['UnitParameter'].get(cvalue_row['Parameter_ID'])
            code = data['UnitDomainElement'].get(cvalue_row['Code_ID'])
            if not constr or not param or not code:
                # TODO warn about this
                continue
            name = code.name
            # TODO add source (not valid in UnitValue itself -- maybe make UnitValueSource table?)
            source = ';'.join(value_row['Source']) if 'Source' in value_row else None

            cvalue = data.add(
                UnitValue, id_,
                id=id_, name=name, contribution=contrib, unit=constr,
                unitparameter=param, unitdomainelement=code)

            DBSession.flush()
            for ex_id in set(cvalue_row.get('Example_IDs', ())):
                example = data['Sentence'].get(ex_id)
                if example:
                    UnitValueSentence(unitvalue=cvalue, sentence=example)
