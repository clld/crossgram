from collections import namedtuple, OrderedDict
from datetime import date
from itertools import chain
import pathlib
import re

from clld.cliutil import Data, bibtex2source
from clld.lib import bibtex
from clldutils import jsonlib
from clldutils.misc import slug
from nameparser import HumanName
from pycldf import iter_datasets
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
    ContributionLanguage,
    Example,
    LParameter,
    CParameter,
    UnitReference,
    UnitSentence,
    UnitValueReference,
    UnitValueSentence,
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
    'Comment': 'comment',
    'Source': 'source'}


SourceTuple = namedtuple(
    'SourceTuple',
    ('bibkey', 'pages', 'source_string', 'source_pk'))


def parse_source(biblio_map, source_string):
    match = re.fullmatch(r'([^[]+)(?:\[([^]]*)\])?', source_string)
    if match and match.group(1):
        bibkey, pages = match.groups()
        source = biblio_map.get(bibkey)
        return SourceTuple(
            bibkey=bibkey,
            pages=pages or '',
            source_string=source_string,
            source_pk=source.pk if source else None)
    else:
        return None


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

    def add_to_database(self, data, language_id_map, intro):
        contrib = data.add(
            CrossgramData,
            self.sid,
            id=self.sid,
            number=self.number,
            published=self.published,
            name=self.md.get('title'),
            description=intro)

        used_languages = {
            row['Language_ID']
            for row in chain(
                self.cldf.get('ValueTable') or (),
                self.cldf.get('ExampleTable') or (),
                self.cldf.get('constructions.csv') or ())
            if row.get('Language_ID')}

        local_lang_ids = set()
        for language_row in self.cldf['LanguageTable']:
            old_id = language_row.get('ID')
            if not old_id or old_id not in used_languages:
                continue

            # Apparently some datasets contain multiple languages sharing the
            # same Glottocode...  So try and use the name to distinguish them
            id_candidate = language_row.get('Glottocode') or old_id
            number = 1
            new_id = id_candidate
            lang = data['Language'].get(new_id)
            while (lang
                and new_id in local_lang_ids
                and slug(lang.name) != slug(language_row.get('Name'))
            ):
                number += 1
                new_id = '{}-{}'.format(id_candidate, number)
                lang = data['Language'].get(new_id)
            local_lang_ids.add(new_id)

            language_id_map[old_id] = new_id
            if not lang:
                lang = data.add(
                    Language,
                    new_id,
                    id=new_id,
                    **map_cols(LANG_MAP, language_row))

            DBSession.flush()
            # TODO add glottocode, iso code, and wals code if available

            DBSession.add(
                ContributionLanguage(
                    language_pk=lang.pk,
                    contribution_pk=contrib.pk))

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
            st = parse_source(biblio_map, example_row.get('Source') or '')
            if st and st.source_pk is not None:
                DBSession.add(SentenceReference(
                    key=st.bibkey,
                    description=st.pages,
                    sentence_pk=example.pk,
                    source_pk=st.source_pk))

        DBSession.flush()

        for constr_row in self.cldf.get('constructions.csv', ()):
            old_id = constr_row.get('ID')
            if not old_id:
                continue
            new_id = '{}-{}'.format(contrib.id, old_id)
            lang_new_id = language_id_map.get(constr_row['Language_ID'])
            lang = data['Language'].get(lang_new_id)
            constr = data.add(
                Construction,
                old_id,
                language=lang,
                contribution=contrib,
                id=new_id,
                **map_cols(CONSTR_MAP, constr_row))

            DBSession.flush()
            for source_string in sorted(set(constr_row.get('Source') or ())):
                st = parse_source(biblio_map, source_string)
                if st and st.source_pk is not None:
                    DBSession.add(UnitReference(
                        key=st.bibkey,
                        description=st.pages,
                        unit_pk=constr.pk,
                        source_pk=st.source_pk))

            for ex_id in sorted(set(constr_row.get('Example_IDs', ()))):
                example = data['Example'].get(ex_id)
                if example:
                    DBSession.add(UnitSentence(unit=constr, sentence=example))

        DBSession.flush()

        valueset_refs = OrderedDict()
        for value_row in self.cldf.get('ValueTable', ()):
            old_id = value_row.get('ID')
            lang_new_id = language_id_map.get(value_row['Language_ID'])
            lang = data['Language'].get(lang_new_id)
            param = data['LParameter'].get(value_row['Parameter_ID'])
            code = data['DomainElement'].get(value_row['Code_ID'])
            value = code.name if code else value_row['Value']
            if not old_id or not lang or not param or not value:
                continue
            new_id = '{}-{}'.format(contrib.id, old_id)

            valueset = data['ValueSet'].get((lang.pk, param.pk))
            if not valueset:
                valueset = data.add(
                    ValueSet, (lang.pk, param.pk), id=new_id, language=lang,
                    parameter=param, contribution=contrib)

            DBSession.flush()
            value = data['Value'].get((valueset.pk, value))
            if not value:
                value = data.add(
                    Value, (valueset.pk, value),
                    id=new_id, name=value, valueset=valueset, domainelement=code)

            for source_string in sorted(set(value_row.get('Source') or ())):
                st = parse_source(biblio_map, source_string)
                if st and st.source_pk is not None:
                    # collect sources for all values in the same value set
                    if valueset.pk not in valueset_refs:
                        valueset_refs[valueset.pk] = list()
                    valueset_refs[valueset.pk].append(st)

            DBSession.flush()
            for ex_id in sorted(set(value_row.get('Example_IDs', ()))):
                example = data['Example'].get(ex_id)
                if example:
                    DBSession.add(ValueSentence(value=value, sentence=example))

        # attach collected sources from values to the value set
        valuesets = DBSession.query(ValueSet)\
            .filter(ValueSet.contribution == contrib)
        for valueset in valuesets:
            source_tuples = sorted(set(valueset_refs.get(valueset.pk, ())))
            for st in source_tuples:
                DBSession.add(ValueSetReference(
                    key=st.bibkey,
                    description=st.pages or None,
                    valueset_pk=valueset.pk,
                    source_pk=st.source_pk))
            valueset.source = ';'.join(st[2] for st in source_tuples)

        for cvalue_row in self.cldf.get('cvalues.csv', ()):
            old_id = cvalue_row.get('ID')
            constr = data['Construction'].get(cvalue_row['Construction_ID'])
            param = data['CParameter'].get(cvalue_row['Parameter_ID'])
            code = data['UnitDomainElement'].get(cvalue_row['Code_ID'])
            value = code.name if code else cvalue_row['Value']
            if not old_id or not constr or not param or not value:
                continue
            new_id = '{}-{}'.format(contrib.id, old_id)

            cvalue = data.add(
                UnitValue, old_id,
                id=new_id, name=value, contribution=contrib, unit=constr,
                unitparameter=param, unitdomainelement=code)

            DBSession.flush()
            for ex_id in sorted(set(cvalue_row.get('Example_IDs') or ())):
                example = data['Example'].get(ex_id)
                if example:
                    DBSession.add(UnitValueSentence(
                        unitvalue=cvalue, sentence=example))

            for source_string in sorted(set(cvalue_row.get('Source') or ())):
                st = parse_source(biblio_map, source_string)
                if st and st.source_pk is not None:
                    DBSession.add(UnitValueReference(
                        key=st.bibkey,
                        description=st.pages or None,
                        unitvalue=cvalue,
                        source_pk=st.source_pk))

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
            cldf_dataset = next(iter_datasets(path / 'cldf'))
        except StopIteration:
            raise ValueError('No cldf metadata file found in {}'.format(path))

        bib_path = path / 'cldf' / 'sources.bib'
        sources = bibtex.Database.from_file(bib_path) if bib_path.exists() else None

        md_path = path / 'metadata.json'
        md = jsonlib.load(md_path) if md_path.exists() else {}

        authors = contrib_md.get('authors') or ()

        submission_id = (
            contrib_md.get('id')
            or md.get('id')
            or cldf_dataset.properties.get('rc:ID')
            or slug(path.name))
        number = int(contrib_md['number'])

        date_match = re.fullmatch('(\d+)-(\d+)-(\d+)', contrib_md['published'])
        assert date_match
        yyyy, mm, dd = date_match.groups()
        published = date(int(yyyy), int(mm), int(dd))

        return cls(
            submission_id, number, published, cldf_dataset, md, authors,
            sources)
