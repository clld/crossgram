from sqlalchemy.orm import joinedload

from clld.db.meta import DBSession
from clld.db.models import common

from clld.web import datatables
from clld.web.datatables.base import (
    DataTable, DetailsRowLinkCol, LinkCol, RefsCol,
)
from clld.web.datatables.contributor import NameCol, ContributionsCol, AddressCol
from clld.web.datatables.unit import DescriptionLinkCol
from clld.web.datatables.unitvalue import UnitValueNameCol

from crossgram import models


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


class Constructions(datatables.Units):

    __constraints__ = [common.Language, models.CrossgramData]

    def base_query(self, query):
        query = super().base_query(query)
        if self.crossgramdata:
            query = query.filter(models.Construction.contribution == self.crossgramdata)
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


class CParameters(datatables.Unitparameters):

    __constraints__ = [models.CrossgramData]

    def base_query(self, query):
        query = super().base_query(query)
        if self.crossgramdata:
            query = query.filter(models.CParameter.contribution == self.crossgramdata)
        return query

    def col_defs(self):
        cols = [
            DetailsRowLinkCol(self, 'd'),
            LinkCol(self, 'name')]
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
        name_col = UnitValueNameCol(self, 'value')
        constr_col = LinkCol(
            self, 'unit', get_obj=lambda i: i.unit, model_col=common.Unit.name)
        refs_col = RefsCol(self, 'source')
        return [constr_col, name_col, refs_col]


class LParameters(datatables.Parameters):

    __constraints__ = [models.CrossgramData]

    def base_query(self, query):
        query = super().base_query(query)
        if self.crossgramdata:
            query = query.filter(models.LParameter.contribution == self.crossgramdata)
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


class Examples(datatables.Sentences):

    __constraints__ = [common.Parameter, common.Language, models.CrossgramData]

    def base_query(self, query):
        query = super().base_query(query)
        if self.crossgramdata:
            query = query.filter(models.Example.contribution == self.crossgramdata)
        return query


def includeme(config):
    config.register_datatable('contributors', ContributionContributors)
    config.register_datatable('parameters', LParameters)
    config.register_datatable('sentences', Examples)
    config.register_datatable('unitparameters', CParameters)
    config.register_datatable('units', Constructions)
    config.register_datatable('unitvalues', CValues)
