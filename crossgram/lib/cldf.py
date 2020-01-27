from clld.scripts.util import Data
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
    Value,
    ValueSentence,
    ValueSet,
    UnitDomainElement,
    UnitValue,
)
from crossgram.models import (
    CrossgramData,
    Construction,
    Example,
    LParameter,
    CParameter,
    UnitValueSentence,
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


def load_cldfbench(path, glottocode_index=None):
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
        or slug(path.name))
    return CLDFBenchSubmission(submission_id, cldf_dataset, md, authors)


class CLDFBenchSubmission:

    def __init__(self, sid, cldf, md, authors):
        self.sid = sid
        self.md = md
        self.cldf = cldf
        self.authors = authors

    def add_to_database(self, data=None, glottocode_index=None):
        data = data or Data()
        contrib = data.add(
            CrossgramData,
            self.sid,
            id=self.sid,
            name=self.md.get('title'),
            description=self.md.get('description'))

        if glottocode_index:
            languages = list(map(glottocode_index.add_glottocode, languages))
        else:
            languages = self.cldf['LanguageTable']

        for language_row in languages:
            # TODO use something more stable to determine duplicate languages
            #  => Glottocode
            id_ = language_row.get('ID')
            if not id_:
                continue
            if id_ not in data['Language']:
                data.add(
                    Language,
                    id_,
                    id=id_,
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
            ContributionContributor(
                ord=i + 1,
                primary=spec.get('primary', True),
                contribution=contrib,
                contributor=author)

        for constr_row in self.cldf.get('constructions.csv', ()):
            old_id = constr_row.get('ID')
            if not old_id:
                continue
            new_id = '{}-{}'.format(contrib.id, old_id)
            lang = data['Language'].get(constr_row['Language_ID'])
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

        # TODO Check for missing/invalid refs

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
            lang = data['Language'].get(example_row['Language_ID'])
            if not old_id or not lang:
                continue
            new_id = '{}-{}'.format(contrib.id, old_id)
            example_row = _merge_glosses(example_row)
            data.add(
                Example,
                old_id,
                language=lang,
                contribution=contrib,
                id=new_id,
                **map_cols(EXAMPLE_MAP, example_row))

        DBSession.flush()

        for value_row in self.cldf.get('ValueTable', ()):
            old_id = value_row.get('ID')
            lang = data['Language'].get(value_row['Language_ID'])
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

            DBSession.flush()
            for ex_id in set(value_row.get('Example_IDs', ())):
                example = data['Sentence'].get(ex_id)
                if example:
                    ValueSentence(value=value, sentence=example)

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
            for ex_id in set(cvalue_row.get('Example_IDs', ())):
                example = data['Sentence'].get(ex_id)
                if example:
                    UnitValueSentence(unitvalue=cvalue, sentence=example)
