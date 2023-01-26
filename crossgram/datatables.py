from sqlalchemy.orm import joinedload

from clld.db.meta import DBSession
from clld.db.models import common
from clld.db.util import get_distinct_values

from clld.web import datatables
from clld.web.datatables.base import (
    Col, DataTable, DetailsRowLinkCol, IdCol, LinkCol, LinkToMapCol,
)
from clld.web.datatables.contribution import ContributorsCol, CitationCol
from clld.web.datatables.contributor import NameCol, ContributionsCol, AddressCol
from clld.web.datatables.sentence import TsvCol
from clld.web.datatables.unitvalue import UnitValueNameCol
from clld.web.datatables.value import ValueNameCol, ValueSetCol
from clld.web.util.helpers import external_link, linked_references

from crossgram import models


class NumberCol(Col):
    __kw__ = {
        'input_size': 'mini',
        'sClass': 'right',
        'sTitle': 'No.',
        'bSearchable': False}


class DateCol(Col):
    __kw__ = {'bSearchable': False}


class GlottocodeCol(Col):
    def format(self, item):
        item = self.get_obj(item)
        if item.glottocode:
            return external_link(
                'http://glottolog.org/resource/languoid/id/' + item.glottocode,
                label=item.glottocode,
                title='Language information at Glottolog')
        else:
            return ''


class RefsCol(Col):

    """Column listing linked sources."""

    __kw__ = dict(bSearchable=False, bSortable=False)

    def format(self, item):
        vs = self.get_obj(item)
        return linked_references(self.dt.req, vs)


class CrossgramDatasets(DataTable):

    def col_defs(self):
        number = NumberCol(
            self, 'number', model_col=models.CrossgramData.number)
        name = LinkCol(self, 'name')
        contributors = ContributorsCol(self, 'contributor')
        date = DateCol(self, 'published')
        data_link = Col(
            self,
            'data_source',
            bSearchable=False,
            bSortable=False,
            sTitle='Data source',
            format=lambda i: i.doi_link() or i.git_link())
        cite_button = CitationCol(self, 'cite')
        return [number, name, contributors, date, data_link, cite_button]


class ContributionContributors(DataTable):
    def base_query(self, query):
        return DBSession.query(common.Contributor) \
            .join(common.ContributionContributor) \
            .join(common.Contribution)

    def col_defs(self):
        name = NameCol(self, 'name')
        contributions = ContributionsCol(self, 'Contributions')
        address = AddressCol(self, 'address')
        return [name, contributions, address]


class Languages(datatables.Languages):

    __constraints__ = [models.CrossgramData]

    def base_query(self, query):
        query = query \
            .join(models.ContributionLanguage) \
            .join(common.Contribution)
        if self.crossgramdata:
            query = query.filter(
                common.Contribution.id == self.crossgramdata.id)
        return query

    def col_defs(self):
        # XXX is the ID really necessary?
        # (maybe for cases where the name is the same?)
        id_ = Col(self, 'id', sTitle='ID', input_size='mini')
        name = LinkCol(self, 'name')
        # NOTE: can't be named 'glottocode' because Language.glottocode is a
        # Python property instead of a sqlalchemy table column.
        glottocode = GlottocodeCol(self, 'glottocode_col', sTitle='Glottocode')
        linktomap = LinkToMapCol(self, 'm')
        if self.crossgramdata:
            return [id_, name, glottocode, linktomap]
        else:
            contrib = ContributionsCol(self, 'contributions')
            return [id_, name, glottocode, contrib, linktomap]


class Constructions(datatables.Units):

    __constraints__ = [common.Language, models.CrossgramData]

    def base_query(self, query):
        query = DBSession.query(models.Construction)

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
        language = LinkCol(
            self, 'language', model_col=common.Language.name,
            get_obj=lambda i: i.language)
        name = LinkCol(self, 'name')
        desc = Col(self, 'description')
        contrib = LinkCol(
            self,
            'contribution',
            model_col=models.CrossgramData.name,
            get_obj=lambda i: i.contribution,
            choices=get_distinct_values(models.CrossgramData.name))

        if self.crossgramdata:
            return [language, name, desc]
        elif self.language:
            return [name, desc, contrib]
        else:
            return [language, name, desc, contrib]


class CParameters(datatables.Unitparameters):

    __constraints__ = [models.CrossgramData]

    def base_query(self, query):
        query = DBSession.query(models.CParameter)
        if self.crossgramdata:
            query = query.filter(
                models.CParameter.contribution_pk == self.crossgramdata.pk)
        else:
            query.join(models.CParameter.contribution)
        return query

    def col_defs(self):
        name = LinkCol(self, 'name')
        desc = Col(self, 'description')
        details = DetailsRowLinkCol(self, 'd')
        if self.crossgramdata:
            return [name, desc, details]
        else:
            # FIXME AAAAHHHHH why does the search/filter not work!?
            #  * Database layout is parallel to LParameters
            #  * Query is parallel to LParameters
            #  * Column defs are parallel to LParameters
            # Every thing is the same.  You can take the code and put it
            # side by side and it's identical.  Still, one works the other
            # doesn't!  WHYYYYYYYY???
            contrib = LinkCol(
                self,
                'contribution',
                model_col=models.CrossgramData.name,
                get_obj=lambda i: i.contribution)
            return [name, desc, contrib, details]


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
        lang = LinkCol(
            self, 'language',
            get_obj=lambda i: i.unit.language,
            model_col=common.Language.name)
        cparam = LinkCol(
            self, 'unitparameter',
            model_col=models.CParameter.name,
            get_obj=lambda i: i.unitparameter,
            sTitle='Construction Parameter')
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
            return [lang, constr, cvalue, source, contrib]
        elif self.unit:
            return [cparam, cvalue, source]
        elif self.language:
            return [constr, cparam, cvalue, source, contrib]
        else:
            return [lang, constr, cparam, cvalue, source, contrib]


class LParameters(datatables.Parameters):

    __constraints__ = [models.CrossgramData]

    def base_query(self, query):
        query = DBSession.query(models.LParameter)
        if self.crossgramdata:
            query = query.filter(
                models.LParameter.contribution_pk == self.crossgramdata.pk)
        else:
            query = query.join(models.LParameter.contribution)
        return query

    def col_defs(self):
        name = LinkCol(self, 'name')
        desc = Col(self, 'description')
        details =  DetailsRowLinkCol(self, 'd')
        if self.crossgramdata:
            return [name, desc, details]
        else:
            contrib = LinkCol(
                self,
                'contribution',
                model_col=models.CrossgramData.name,
                get_obj=lambda i: i.contribution)
            return [name, desc, contrib, details]


class LValues(datatables.Values):

    __constraints__ = [common.Parameter, common.Contribution, common.Language]

    def base_query(self, query):
        query = DBSession.query(common.Value) \
            .join(common.Value.domainelement, isouter=True) \
            .join(common.ValueSet) \
            .join(common.ValueSet.references, isouter=True) \
            .join(common.ValueSetReference.source, isouter=True)

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
        value = ValueNameCol(self, 'value')
        if self.parameter and self.parameter.domain:
            value.choices = [de.name for de in self.parameter.domain]

        lang = LinkCol(
            self,
            'language',
            model_col=common.Language.name,
            get_object=lambda i: i.valueset.language)
        param = LinkCol(
            self,
            'parameter',
            sTitle=self.req.translate('Parameter'),
            model_col=common.Parameter.name,
            get_object=lambda i: i.valueset.parameter)
        contrib = LinkCol(
            self,
            'contribution',
            model_col=common.Contribution.name,
            get_object=lambda i: i.valueset.contribution)
        sources = RefsCol(self, 'source')
        details = DetailsRowLinkCol(self, 'd')

        # XXX: is `contribution` *ever* set in crossgram?
        # XXX: can `parameter` and `language` be set at the same time?
        # ^ that would return a single value…
        if self.parameter:
            link_to_map = LinkToMapCol(
                self, 'm', get_object=lambda i: i.valueset.language)
            # XXX add contribution col?
            return [lang, value, sources, details, link_to_map]
        elif self.language:
            return [param, value, sources, contrib, details]
        else:
            # XXX why valueset?
            valueset = ValueSetCol(
                self, 'valueset', bSearchable=False, bSortable=False)
            return [lang, param, valueset, sources, contrib, details]


class Examples(datatables.Sentences):

    __constraints__ = [common.Parameter, common.Language, models.CrossgramData]

    def base_query(self, query):
        query = super().base_query(query)
        if self.crossgramdata:
            query = query.filter(models.Example.contribution == self.crossgramdata)
        return query.order_by(models.Language.name)

    def col_defs(self):
        cols = [
            LinkCol(
                self,
                'language',
                model_col=common.Language.name,
                get_obj=lambda i: i.language,
                bSortable=not self.language,
                bSearchable=not self.language),
            LinkCol(self, 'name', sTitle='Primary text', sClass="object-language"),
            TsvCol(self, 'analyzed', sTitle='Analyzed text'),
            TsvCol(self, 'gloss', sClass="gloss"),
            Col(self,
                'description',
                sTitle=self.req.translate('Translation'),
                sClass="translation"),
            DetailsRowLinkCol(self, 'd'),
        ]
        if not self.crossgramdata:
            cols.append(LinkCol(
                self,
                'contribution',
                model_col=models.CrossgramData.name,
                get_obj=lambda i: i.contribution))
        return cols


class Sources(datatables.Sources):

    __constraints__ = [common.Language, models.CrossgramData]

    def base_query(self, query):
        query = super().base_query(query)
        if self.crossgramdata:
            # FIXME Sorting by contribution throws an error
            query = query\
                .join(models.CrossgramDataSource)\
                .filter(models.CrossgramDataSource.contribution == self.crossgramdata)
        return query

    def col_defs(self):
        cols = super().col_defs()
        if not self.crossgramdata:
            cols.append(LinkCol(
                self,
                'contribution',
                model_col=models.CrossgramData.name,
                get_obj=lambda i: i.contribution))
        return cols


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
