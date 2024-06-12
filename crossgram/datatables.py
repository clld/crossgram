from itertools import chain

from clld.db.meta import DBSession
from clld.db.models import common
from clld.db.util import get_distinct_values, icontains
from clld.web import datatables
from clld.web.datatables.base import (
    Col, DataTable, DetailsRowLinkCol, LinkCol, LinkToMapCol,
)
from clld.web.datatables.contribution import ContributorsCol
from clld.web.datatables.contributor import NameCol, ContributionsCol, AddressCol
from clld.web.datatables.sentence import TsvCol
from clld.web.datatables.unitvalue import UnitValueNameCol
from clld.web.datatables.value import ValueNameCol, ValueSetCol
from clld.web.util.helpers import (
    map_marker_img, link, external_link, gbs_link, linked_references,
)
from clld.web.util.htmllib import HTML
from clld_glottologfamily_plugin.models import Family
from sqlalchemy import func, null, select
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import case

from crossgram import models
from crossgram.lib.horrible_denormaliser import BlockDecoder


# Columns

class NumberCol(Col):
    __kw__ = {
        'input_size': 'mini',
        'sClass': 'right',
        'sTitle': 'No.',
        'bSearchable': False}


class DateCol(Col):
    __kw__ = {'bSearchable': False, 'sTitle': 'Year'}

    def format(self, item):
        return item.published.year


class AffiliationCol(Col):
    def format(self, item):
        if item.url:
            return external_link(item.url, label=item.address)
        else:
            return item.address


class CustomLangNameCol(Col):

    def __init__(self, dt, name, contribution_pk, *args, **kwargs):
        self._contribution_pk = contribution_pk
        self._decoder = BlockDecoder(contribution_pk)
        super().__init__(dt, name, *args, **kwargs)

    def order(self):
        return case(
            (models.Variety.custom_names.like(self._decoder.sql_has_contrib),
             func.substring(models.Variety.custom_names,
                            self._decoder.regex_get_value)),
            else_=models.Variety.name)

    def search(self, query_string):
        if self._contribution_pk:
            return case(
                (models.Variety.custom_names.like(self._decoder.sql_has_contrib),
                 models.Variety.custom_names.op('~*')(
                     self._decoder.regex_search_value(query_string))),
                else_=icontains(models.Variety.name, query_string))
        else:
            return icontains(models.Variety.name, query_string)

    def format(self, item):
        obj = self.get_obj(item)
        if not obj:
            return ''
        label = (
            self._decoder.extract_value(obj.custom_names)
            or obj.name
            or str(obj))
        return link(self.dt.req, obj, label=label)


class GlottocodeCol(Col):
    def format(self, item):
        item = self.get_obj(item)
        if item.glottolog_id:
            return external_link(
                'http://glottolog.org/resource/languoid/id/{}'.format(
                    item.glottolog_id),
                label=item.glottolog_id,
                title='Language information at Glottolog')
        else:
            return ''


class CustomFamilyCol(Col):
    def __init__(
        self, dt, name, language_cls, link=False, contribution_pk=None, **kw
    ):
        self._link = link
        self._col = getattr(language_cls, 'family')
        if contribution_pk is None:
            family_query = select(Family.id, Family.name).order_by(Family.name)
        else:
            family_query = select(Family.id, Family.name) \
                .join_from(models.ContributionLanguage, models.Variety) \
                .join_from(models.Variety, Family) \
                .where(models.ContributionLanguage.contribution_pk == contribution_pk) \
                .order_by(Family.name) \
                .distinct()
        kw['choices'] = [('isolate', '--none--')]
        kw['choices'].extend(
            (id_, name)
            for id_, name in DBSession.execute(family_query))
        Col.__init__(self, dt, name, **kw)

    def order(self):
        return Family.name

    def search(self, qs):
        if qs == 'isolate':
            return self._col == null()
        return Family.id == qs

    def format(self, item):
        item = self.get_obj(item)
        if item.family:
            label = link(self.dt.req, item.family) if self._link else item.family.name
        else:
            label = 'isolate'
        return HTML.div(map_marker_img(self.dt.req, item), ' ', label)


class CountCol(Col):
    __kw__ = {
        'input_size': 'mini',
        'sClass': 'right'}

    def get_value(self, item):
        return super().get_value(item) or 0

    def order(self):
        # When a count is missing, assume there are 0 counted things.
        return case(
            [(self.model_col.is_(None), 0)],
            else_=self.model_col)


class ExampleCountCol(CountCol):
    def format(self, item):
        item = self.get_obj(item)
        count = self.get_value(item)
        if count == 0:
            return count
        else:
            return link(
                self.dt.req,
                item,
                label=count,
                url_kw={'_anchor': 'texamples'})


class MoreIntuitiveValueNameCol(ValueNameCol):
    """More intuitive value name column (at least for me).

    Searching in the value table returned unexpected results because
    the column searched the *description* instead of the name shown in
    the column itself.  This tripped me up a few times.
    """
    def search(self, qs):
        if self.dt.parameter and self.dt.parameter.domain:
            return common.DomainElement.name == qs
        else:
            return icontains(common.Value.name, qs)


class RefsCol(Col):

    """Column listing linked sources."""

    __kw__ = {'bSearchable': False, 'bSortable': False}

    def format(self, item):
        valueset = self.get_obj(item)
        return (
            linked_references(self.dt.req, valueset)
            or getattr(valueset, 'source_comment', None)
            or '')


def _generate_separators(iterable):
    first_item = True
    for item in iterable:
        if first_item:
            first_item = False
        else:
            yield '; '
        yield item


def semicolon_separated_span(iterable):
    return HTML.span(*_generate_separators(iterable))


class SourceLanguageCol(Col):

    """Column listing linked languages of a source."""

    __kw__ = {'bSearchable': False, 'bSortable': False}

    def format(self, item):
        source = self.get_obj(item)
        return semicolon_separated_span(
            link(self.dt.req, ref.language)
            for ref in source.languagereferences
            if ref.language)


def format_source_reference(req, ref):
    desc = ': %s' % ref.description if ref.description else ''
    gbs = gbs_link(ref.source, pages=ref.description)
    return HTML.span(
        link(req, ref.source),
        HTML.span(desc, class_='pages'),
        ' ' if gbs else '',
        gbs,
        class_='citation',
    )


class FilteredLanguageSourcesCol(Col):

    """Column showing sources for a language, filtered by contribution."""

    __kw__ = {'bSearchable': False, 'bSortable': False}

    def __init__(self, *args, contribution_pk=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._contribution_pk = contribution_pk
        self._decoder = BlockDecoder(contribution_pk)

    def in_contribution(self, source):
        return (
            self._contribution_pk is None
            or source.contribution_pk == self._contribution_pk)

    def format(self, item):
        language = self.get_obj(item)
        linked_refs = [
            ref
            for ref in language.references
            if ref.source and self.in_contribution(ref.source)]
        if linked_refs:
            return semicolon_separated_span(
                format_source_reference(self.dt.req, ref)
                for ref in linked_refs)
        elif self._contribution_pk:
            return self._decoder.extract_value(language.source_comments)
        else:
            return '; '.join(
                self._decoder.iter_values(language.source_comments))


class ParameterTopicsCol(Col):
    """Column listing linked topics for an L parameter."""
    # NOTE: Also duck-types its way through C parameters

    __kw__ = {'bSearchable': False, 'bSortable': False}

    def format(self, item):
        obj = self.get_obj(item)
        topics = (assoc.topic for assoc in obj.topic_assocs)
        return '; '.join(
            link(self.dt.req, topic, label=topic.name)
            for topic in topics)


class TopicParametersCol(Col):
    """Column listing linked parameters for a topic."""

    __kw__ = {'bSearchable': False, 'bSortable': False}

    def format(self, item):
        obj = self.get_obj(item)
        lparameters = (assoc.parameter for assoc in obj.parameter_assocs)
        cparameters = (assoc.unitparameter for assoc in obj.unitparameter_assocs)
        return '; '.join(
            link(self.dt.req, parameter, label=parameter.name)
            for parameter in chain(lparameters, cparameters))


def object_examples(contribution, obj):
    return [
        example
        for example in getattr(obj, 'sentences', ())
        if not contribution
        or example.contribution_pk == contribution.pk]


def construction_examples(_, construction):
    # NOTE: duck-typing this for cvalues as well
    # no need to filter by contrib; constructions are tied to them anyways
    return [
        assoc.sentence
        for assoc in construction.sentence_assocs]


class ExamplesCol(Col):
    """Column listing linked examples."""

    __kw__ = {'bSearchable': False, 'bSortable': False}

    def __init__(self, *args, example_collector=object_examples, **kwargs):
        super().__init__(*args, **kwargs)
        self._example_collector = example_collector

    def format(self, item):
        obj = self.get_obj(item)
        contribution = getattr(self.dt, 'crossgramdata', None)

        def _label(example):
            if contribution:
                return f'({example.number})'
            else:
                return f'({example.id})'

        examples = self._example_collector(contribution, obj)
        if contribution:
            examples.sort(key=lambda ex: ex.number)
        else:
            examples.sort(key=lambda ex: (ex.contribution.number, ex.number))
        return semicolon_separated_span(
            link(self.dt.req, example, label=_label(example))
            for example in examples)


# Datatables

class CrossgramDatasets(DataTable):

    def col_defs(self):
        # number = NumberCol(
        #     self, 'number', model_col=models.CrossgramData.number)
        name = LinkCol(self, 'name')
        contributors = ContributorsCol(self, 'contributor', sTitle='Authors')
        # date = DateCol(self, 'published')
        year = Col(
            self, 'original_year', sTitle='Year',
            model_col=models.CrossgramData.original_year)
        data_link = Col(
            self,
            'data_source',
            bSearchable=False,
            bSortable=False,
            sTitle='Data source',
            format=lambda i: i.doi_link() or i.git_link())
        # cite_button = CitationCol(self, 'cite')
        return [name, contributors, year, data_link]

    def get_options(self):
        return {'aaSorting': [[2, 'asc']]}


class ContributionContributors(DataTable):
    def base_query(self, query):
        return DBSession.query(common.Contributor) \
            .join(common.Contributor.contribution_assocs) \
            .join(common.ContributionContributor.contribution)

    def col_defs(self):
        name = NameCol(self, 'name')
        contributions = ContributionsCol(self, 'Contributions')
        address = AffiliationCol(self, 'address', sTitle='Affiliation')
        return [name, contributions, address]


class Languages(datatables.Languages):

    __constraints__ = [models.CrossgramData]

    def base_query(self, query):
        query = DBSession.query(models.Variety) \
            .join(models.Variety.family, isouter=True) \
            .join(models.Variety.contribution_assocs) \
            .options(
                joinedload(common.Language.references)
                .joinedload(models.LanguageReference.source),
                joinedload(common.Language.sentences))

        if self.crossgramdata:
            query = query.filter(
                models.ContributionLanguage.contribution_pk
                == self.crossgramdata.pk)
        else:
            query = query.join(
                models.ContributionLanguage.contribution,
                isouter=True)

        return query

    def col_defs(self):
        # NOTE: can't be named 'glottocode' because Language.glottocode is a
        # Python property instead of a sqlalchemy table column.
        glottocode = GlottocodeCol(
            self,
            'glottocode_col',
            model_col=models.Variety.glottolog_id,
            sTitle='Glottocode')
        contribution_pk = self.crossgramdata.pk if self.crossgramdata else None
        source = FilteredLanguageSourcesCol(
            self, 'source', contribution_pk=contribution_pk)
        family = CustomFamilyCol(
            self, 'family', models.Variety, contribution_pk=contribution_pk)
        linktomap = LinkToMapCol(self, 'm')
        examples = ExamplesCol(self, 'examples')
        if self.crossgramdata:
            custom_name = CustomLangNameCol(
                self, 'custom_name',
                contribution_pk=self.crossgramdata.pk,
                sTitle='Name')
            return [custom_name, glottocode, family, source, examples]
        else:
            # example_count = ExampleCountCol(
            #     self,
            #     'example_count',
            #     model_col=models.Variety.example_count,
            #     sTitle='Examples')
            name = LinkCol(self, 'name')
            contrib = ContributionsCol(self, 'contributions')
            return [
                name, glottocode, family, contrib, source, examples,
                linktomap]


class Constructions(datatables.Units):

    __constraints__ = [common.Language, models.CrossgramData]

    def base_query(self, query):
        query = DBSession.query(models.Construction).options(
            joinedload(common.Unit.sentence_assocs)
            .joinedload(models.UnitSentence.sentence))

        if self.crossgramdata:
            query = query.filter(
                models.Construction.contribution_pk == self.crossgramdata.pk)
        else:
            query = query.join(models.Construction.contribution)

        if self.language:
            query = query.filter(
                models.Construction.language_pk == self.language.pk)
        else:
            query = query.join(models.Construction.language)

        return query

    def col_defs(self):
        name = LinkCol(self, 'name', sTitle='Construction')
        desc = Col(self, 'description')
        contrib_query = select(models.CrossgramData.name)\
            .join_from(models.Construction, models.CrossgramData)\
            .order_by(models.CrossgramData.name)
        if self.language:
            contrib_query = contrib_query.filter(
                models.Construction.language_pk == self.language.pk)
        contrib_query = contrib_query.distinct()
        contribs_with_constr = [c for c, in DBSession.execute(contrib_query)]
        contrib = LinkCol(
            self,
            'contribution',
            model_col=models.CrossgramData.name,
            get_obj=lambda i: i.contribution,
            choices=contribs_with_constr)
        examples = ExamplesCol(
            self, 'examples', example_collector=construction_examples)
        if self.crossgramdata:
            language = CustomLangNameCol(
                self, 'custom_name', self.crossgramdata.pk,
                get_obj=lambda i: i.language,
                sTitle='Language')
            return [language, name, desc, examples]
        elif self.language:
            return [name, desc, examples, contrib]
        else:
            language = LinkCol(
                self, 'language', model_col=common.Language.name,
                get_obj=lambda i: i.language)
            return [language, name, desc, examples, contrib]


class CParameters(datatables.Unitparameters):

    __constraints__ = [models.CrossgramData]

    def base_query(self, query):
        if self.crossgramdata:
            query = query.filter(
                models.CParameter.contribution_pk == self.crossgramdata.pk)
        else:
            query = query.join(models.CParameter.contribution)
        query = query.options(
            joinedload(common.UnitParameter.topic_assocs)
            .joinedload(models.UnitParameterTopic.topic))
        return query

    def col_defs(self):
        # TODO: list of linked topics
        name = LinkCol(self, 'name', sTitle='C-Parameter')
        desc = Col(self, 'description')
        langcount = CountCol(
            self,
            'language_count',
            model_col=models.CParameter.language_count,
            sTitle='Representation')
        details = DetailsRowLinkCol(self, 'd', button_text='Values')
        topics = ParameterTopicsCol(self, 'Topics')
        if self.crossgramdata:
            return [details, name, desc, topics, langcount]
        else:
            contrib_query = select(models.CrossgramData.name)\
                .join_from(models.CParameter, models.CrossgramData)\
                .order_by(models.CrossgramData.name)\
                .distinct()
            contribs_with_cparam = [
                c for c, in DBSession.execute(contrib_query)]
            contrib = LinkCol(
                self,
                'contribution',
                model_col=models.CrossgramData.name,
                get_obj=lambda i: i.contribution,
                choices=contribs_with_cparam)
            return [details, contrib, name, desc, topics, langcount]


class CValues(datatables.Unitvalues):

    __constraints__ = [
        common.Unit,
        common.UnitParameter,
        common.Contribution,
        common.Language]

    def base_query(self, query):
        query = DBSession.query(common.UnitValue) \
            .join(common.UnitValue.unit) \
            .join(common.UnitValue.unitdomainelement, isouter=True) \
            .join(common.UnitValue.references, isouter=True) \
            .join(models.UnitValueReference.source, isouter=True)

        if self.unitparameter:
            query = query.filter(
                common.UnitValue.unitparameter_pk == self.unitparameter.pk)
        else:
            query = query.join(common.UnitValue.unitparameter)

        if self.contribution:
            query = query.filter(
                common.UnitValue.contribution_pk == self.contribution.pk)
        else:
            query = query.join(common.UnitValue.contribution)

        if self.language:
            query = query.filter(
                common.Unit.language_pk == self.language.pk)
        else:
            query = query.join(common.Unit.language)

        if self.unit:
            query = query.options(
                joinedload(models.CValue.sentence_assocs)
                .joinedload(models.UnitValueSentence.sentence))
            query = query.filter(
                common.UnitValue.unit_pk == self.unit.pk)

        return query

    def col_defs(self):
        cvalue = UnitValueNameCol(self, 'value')
        if self.unitparameter and self.unitparameter.domain:
            cvalue.choices = [de.name for de in self.unitparameter.domain]

        constr = LinkCol(
            self, 'unit',
            get_obj=lambda i: i.unit, model_col=common.Unit.name)
        cparam = LinkCol(
            self, 'unitparameter',
            model_col=models.CParameter.name,
            get_obj=lambda i: i.unitparameter,
            sTitle='Construction Parameter')
        comment = Col(self, 'description', sTitle='Comment')
        source = RefsCol(self, 'source')
        contrib = LinkCol(
            self,
            'contribution',
            model_col=models.Contribution.name,
            get_obj=lambda i: i.contribution,
            choices=get_distinct_values(models.Contribution.name))

        # XXX: is `contribution` ever set?
        # XXX: can `unitparameter` and `language` be set at the same time?
        # ^ that might actually make sense
        if self.unitparameter:
            lang = CustomLangNameCol(
                self, 'custom_name', self.unitparameter.contribution_pk,
                get_obj=lambda i: i.unit.language,
                sTitle='Language')
            return [contrib, lang, constr, cvalue, comment, source]
        elif self.unit:
            examples = ExamplesCol(
                self, 'examples', example_collector=construction_examples)
            return [cparam, cvalue, comment, examples, source]
        elif self.language:
            return [contrib, constr, cparam, cvalue, comment, source]
        else:
            lang = LinkCol(
                self, 'language',
                get_obj=lambda i: i.unit.language,
                model_col=common.Language.name)
            return [contrib, lang, constr, cparam, cvalue, comment, source]


class LParameters(datatables.Parameters):

    __constraints__ = [models.CrossgramData]

    def base_query(self, query):
        if self.crossgramdata:
            query = query.filter(
                models.LParameter.contribution_pk == self.crossgramdata.pk)
        else:
            query = query.join(models.LParameter.contribution)
        query = query.options(
            joinedload(common.Parameter.topic_assocs)
            .joinedload(models.ParameterTopic.topic))
        return query

    def col_defs(self):
        # TODO: list of linked topics
        name = LinkCol(self, 'name', sTitle='L-Parameter')
        desc = Col(self, 'description')
        langcount = CountCol(
            self,
            'language_count',
            model_col=models.LParameter.language_count,
            sTitle='Representation')
        details = DetailsRowLinkCol(self, 'd', button_text='Values')
        topics = ParameterTopicsCol(self, 'Topics')
        if self.crossgramdata:
            return [details, name, desc, topics, langcount]
        else:
            contrib_query = select(models.CrossgramData.name)\
                .join_from(models.LParameter, models.CrossgramData)\
                .order_by(models.CrossgramData.name)\
                .distinct()
            contribs_with_lparam = [
                c for c, in DBSession.execute(contrib_query)]
            contrib = LinkCol(
                self,
                'contribution',
                model_col=models.CrossgramData.name,
                get_obj=lambda i: i.contribution,
                choices=contribs_with_lparam)
            return [details, contrib, name, desc, topics, langcount]


class LValues(datatables.Values):

    __constraints__ = [common.Parameter, common.Contribution, common.Language]

    def base_query(self, query):
        query = DBSession.query(common.Value) \
            .join(common.Value.domainelement, isouter=True) \
            .join(common.ValueSet) \
            .options(
                joinedload(common.Value.valueset)
                .joinedload(common.ValueSet.references)
                .joinedload(common.ValueSetReference.source))

        if self.parameter:
            query = query.filter(
                common.ValueSet.parameter_pk == self.parameter.pk)
        else:
            query = query.join(common.ValueSet.parameter)

        if self.language:
            query = query.filter(
                common.ValueSet.language_pk == self.language.pk)
        else:
            query = query.join(common.ValueSet.language)

        if self.contribution:
            query = query.filter(
                common.ValueSet.contribution_pk == self.contribution.pk)
        else:
            query = query.join(common.ValueSet.contribution)

        return query

    def col_defs(self):
        value = MoreIntuitiveValueNameCol(self, 'value', common.Value.name)
        if self.parameter and self.parameter.domain:
            value.choices = [de.name for de in self.parameter.domain]

        param = LinkCol(
            self,
            'parameter',
            sTitle=self.req.translate('Parameter'),
            model_col=common.Parameter.name,
            get_object=lambda i: i.valueset.parameter)
        contrib_query = select(common.Contribution.name)\
            .join_from(common.ValueSet, common.Contribution)\
            .order_by(common.Contribution.name)
        if self.language:
            contrib_query = contrib_query.filter(
                common.ValueSet.language_pk == self.language.pk)
        if self.parameter:
            contrib_query = contrib_query.filter(
                common.ValueSet.parameter_pk == self.parameter.pk)
        contrib_query = contrib_query.distinct()
        contribs_with_lval = [
            c for c, in DBSession.execute(contrib_query)]
        contrib = LinkCol(
            self,
            'contribution',
            model_col=common.Contribution.name,
            get_object=lambda i: i.valueset.contribution,
            choices=contribs_with_lval)
        sources = RefsCol(self, 'source', get_object=lambda i: i.valueset)
        comment = Col(self, 'description', sTitle='Comment')
        # details = DetailsRowLinkCol(self, 'd')

        # XXX: is `contribution` *ever* set in crossgram?
        # XXX: can `parameter` and `language` be set at the same time?
        # ^ that would return a single value…
        if self.parameter:
            # link_to_map = LinkToMapCol(
            #     self, 'm', get_object=lambda i: i.valueset.language)
            lang = CustomLangNameCol(
                self, 'custom_name', self.parameter.contribution_pk,
                get_obj=lambda i: i.valueset.language,
                sTitle='Language')
            # XXX add contribution col?
            return [lang, value, comment, sources]
        elif self.language:
            return [contrib, param, value, comment, sources]
        else:
            lang = LinkCol(
                self,
                'language',
                model_col=common.Language.name,
                get_object=lambda i: i.valueset.language)
            # XXX why valueset?
            valueset = ValueSetCol(
                self, 'valueset', bSearchable=False, bSortable=False)
            return [contrib, lang, param, valueset, comment, sources]


class Examples(datatables.Sentences):

    __constraints__ = [common.Parameter, common.Language, models.CrossgramData]

    def base_query(self, query):
        query = super().base_query(query) \
            .options(
                joinedload(common.Sentence.references)
                .joinedload(common.SentenceReference.source))

        if self.crossgramdata:
            query = query.filter(models.Example.contribution_pk == self.crossgramdata.pk)
        else:
            query = query.join(models.Example.contribution)

        return query

    def col_defs(self):
        primary = LinkCol(
            self, 'name', sTitle='Primary text', sClass="object-language")
        # analyzed = TsvCol(self, 'analyzed', sTitle='Analyzed text')
        gloss = TsvCol(self, 'gloss', sClass="gloss")
        translation = Col(
            self,
            'description',
            sTitle=self.req.translate('Translation'),
            sClass="translation")
        source = RefsCol(self, 'source')
        details = DetailsRowLinkCol(self, 'd')

        if self.crossgramdata:
            number = NumberCol(self, 'number', model_col=models.Example.number)
            language = CustomLangNameCol(
                self, 'custom_name', self.crossgramdata.pk,
                get_obj=lambda i: i.language,
                sTitle='Language')
            return [number, language, primary, gloss, translation, source, details]
        else:
            language = LinkCol(
                self,
                'language',
                model_col=common.Language.name,
                get_obj=lambda i: i.language,
                bSortable=not self.language,
                bSearchable=not self.language)
            contrib_query = select(models.CrossgramData.name)\
                .join_from(models.Example, models.CrossgramData)\
                .order_by(models.CrossgramData.name)\
                .distinct()
            contribs_with_ex = [
                c for c, in DBSession.execute(contrib_query)]
            contrib = LinkCol(
                self,
                'contribution',
                model_col=models.CrossgramData.name,
                get_obj=lambda i: i.contribution,
                choices=contribs_with_ex)
            return [
                language, primary, gloss, translation, source, contrib,
                details]

    def get_options(self):
        if self.crossgramdata:
            return {'aaSorting': [[1, 'asc']]}
        else:
            return {}


class Sources(datatables.Sources):

    __constraints__ = [common.Language, models.CrossgramData]

    def base_query(self, query):
        query = DBSession.query(models.CrossgramDataSource)

        if self.language:
            query = query\
                .join(models.CrossgramDataSource.languages)\
                .filter(models.LanguageReference.language_pk == self.language.pk)
        else:
            query = query.options(
                joinedload(models.CrossgramDataSource.languagereferences)
                .joinedload(models.LanguageReference.language))

        if self.crossgramdata:
            query = query.filter(
                models.CrossgramDataSource.contribution_pk
                == self.crossgramdata.pk)
        else:
            query = query.join(models.CrossgramDataSource.contribution)

        return query

    def col_defs(self):
        details = DetailsRowLinkCol(self, 'd')
        name = LinkCol(self, 'name')
        title = Col(
            self,
            'description',
            sTitle='Title',
            format=lambda i: HTML.span(i.description))
        author = Col(self, 'author')
        languages = SourceLanguageCol(self, 'languages')
        year = Col(self, 'year')
        if self.crossgramdata:
            return [details, name, title, author, year, languages]
        else:
            contrib_query = select(models.CrossgramData.name)\
                .join_from(models.CrossgramDataSource, models.CrossgramData)\
                .order_by(models.CrossgramData.name)\
                .distinct()
            contribs_with_src = [
                c for c, in DBSession.execute(contrib_query)]
            contrib = LinkCol(
                self,
                'contribution',
                model_col=models.CrossgramData.name,
                get_obj=lambda i: i.contribution,
                choices=contribs_with_src)
            return [name, title, author, year, contrib, languages, details]


class Topics(DataTable):

    def base_query(self, query):
        return query.options(
            joinedload(models.Topic.parameter_assocs)
            .joinedload(models.ParameterTopic.parameter),
            joinedload(models.Topic.unitparameter_assocs)
            .joinedload(models.UnitParameterTopic.unitparameter))

    def col_defs(self):
        return [
            LinkCol(self, 'name', sTitle='Topic'),
            # TODO: link to grammaticon
            Col(self, 'grammacode'),
            Col(self, 'description'),
            TopicParametersCol(self, 'parameters', sTitle='Parameters'),
        ]


def includeme(config):
    config.register_datatable('contributions', CrossgramDatasets)
    config.register_datatable('contributors', ContributionContributors)
    config.register_datatable('languages', Languages)
    config.register_datatable('parameters', LParameters)
    config.register_datatable('sentences', Examples)
    config.register_datatable('values', LValues)
    config.register_datatable('unitparameters', CParameters)
    config.register_datatable('units', Constructions)
    config.register_datatable('unitvalues', CValues)
    config.register_datatable('sources', Sources)
    config.register_datatable('topics', Topics)
