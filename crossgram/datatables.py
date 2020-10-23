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
from clld.web.datatables.unit import DescriptionLinkCol
from clld.web.datatables.unitvalue import UnitValueNameCol
from clld.web.util.helpers import linked_references

from crossgram import models


class NumberCol(Col):
    __kw__ = {
        'input_size': 'mini',
        'sClass': 'right',
        'sTitle': 'No.',
        'bSearchable': False}


class DateCol(Col):
    __kw__ = {'bSearchable': False}


class RefsCol(Col):

    """Column listing linked sources."""

    __kw__ = dict(bSearchable=False, bSortable=False)

    def format(self, item):
        vs = self.get_obj(item)
        return linked_references(self.dt.req, vs)


class CrossgramDatasets(DataTable):

    def col_defs(self):
        return [
            NumberCol(self, 'number', model_col=models.CrossgramData.number),
            LinkCol(self, 'name'),
            ContributorsCol(self, 'contributor'),
            DateCol(self, 'published'),
            Col(
                self,
                'data_source',
                bSearchable=False,
                bSortable=False,
                sTitle='Data source',
                format=lambda i: i.doi_link() or i.git_link()),
            CitationCol(self, 'cite'),
        ]


class ContributionContributors(DataTable):
    def base_query(self, query):
        return DBSession.query(common.Contributor) \
            .join(common.ContributionContributor) \
            .join(common.Contribution)

    def col_defs(self):
        return [
            NameCol(self, 'name'),
            ContributionsCol(self, 'Contributions'),
            AddressCol(self, 'address'),
        ]


class Languages(datatables.Languages):

    def base_query(self, query):
        return DBSession.query(common.Language) \
            .join(models.ContributionLanguage) \
            .join(common.Contribution)

    def col_defs(self):
        return [
            IdCol(self, 'id'),
            LinkCol(self, 'name'),
            LinkToMapCol(self, 'm'),
            ContributionsCol(self, 'contributions')
        ]


class Constructions(datatables.Units):

    __constraints__ = [common.Language, models.CrossgramData]

    def base_query(self, query):
        query = super()\
                .base_query(query)\
                .join(models.CrossgramData)\
                .options(joinedload(models.Construction.contribution))
        if self.crossgramdata:
            query = query.filter(models.Construction.contribution == self.crossgramdata)
        if not self.language:
            query = query.order_by(common.Language.name)
        return query

    def col_defs(self):
        cols= [
            LinkCol(
                self, 'language', model_col=common.Language.name,
                get_obj=lambda i: i.language),
            LinkCol(self, 'name'),
            DescriptionLinkCol(self, 'description'),
        ]
        if not self.crossgramdata:
            cols.append(LinkCol(
                self,
                'contribution',
                model_col=models.CrossgramData.name,
                get_obj=lambda i: i.contribution,
                choices=get_distinct_values(models.CrossgramData.name)))
        return cols


class CParameters(datatables.Unitparameters):

    __constraints__ = [models.CrossgramData]

    def base_query(self, query):
        query = super()\
                .base_query(query)\
                .join(models.CrossgramData)\
                .options(joinedload(models.CParameter.contribution))
        if self.crossgramdata:
            query = query.filter(models.CParameter.contribution == self.crossgramdata)
        return query

    def col_defs(self):
        cols = [
            DetailsRowLinkCol(self, 'd'),
            LinkCol(self, 'name'),
            Col(self, 'description')]
        if not self.crossgramdata:
            cols.append(LinkCol(
                self,
                'contribution',
                model_col=models.CrossgramData.name,
                get_obj=lambda i: i.contribution))
        return cols


class CValues(datatables.Unitvalues):

    def base_query(self, query):
        query = super().base_query(query)
        q = query.options(
            joinedload(common.UnitValue.references)\
                .joinedload(models.UnitValueReference.source))
        return q

    def col_defs(self):
        cols = []
        if not self.unitparameter:
            cols.append(LinkCol(
                self, 'unitparameter',
                model_col=models.CParameter.name,
                get_obj=lambda i: i.unitparameter,
                sTitle='Construction Parameter'))
        if not self.unit:
            cols.append(LinkCol(
                self, 'unit',
                get_obj=lambda i: i.unit, model_col=common.Unit.name))
        cols.extend((
            UnitValueNameCol(self, 'value'),
            RefsCol(self, 'source')))
        if not self.unitparameter and not self.unit and not self.contribution:
            cols.append(LinkCol(
                self,
                'contribution',
                model_col=models.CrossgramData.name,
                get_obj=lambda i: i.contribution))
        return cols


class LParameters(datatables.Parameters):

    __constraints__ = [models.CrossgramData]

    def base_query(self, query):
        query = super()\
                .base_query(query)\
                .join(models.CrossgramData)\
                .options(joinedload(models.LParameter.contribution))
        if self.crossgramdata:
            query = query.filter(models.LParameter.contribution == self.crossgramdata)
        return query

    def col_defs(self):
        cols = [
            DetailsRowLinkCol(self, 'd'),
            LinkCol(self, 'name'),
            Col(self, 'description')
        ]
        if not self.crossgramdata:
            cols.append(LinkCol(
                self,
                'contribution',
                model_col=models.CrossgramData.name,
                get_obj=lambda i: i.contribution))
        return cols


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
    config.register_datatable('unitparameters', CParameters)
    config.register_datatable('units', Constructions)
    config.register_datatable('unitvalues', CValues)
    config.register_datatable('sources', Sources)
