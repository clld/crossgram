from zope.interface import implementer
from sqlalchemy import (
    Column,
    String,
    Unicode,
    Integer,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    Date,
)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property

from clld import interfaces
from clld.db.meta import Base, CustomModelMixin
from clld.db.models.common import (
    Contribution,
    Parameter,
    Sentence,
    Source,
    Unit,
    UnitParameter,
)


@implementer(interfaces.IContribution)
class CrossgramData(CustomModelMixin, Contribution):
    pk = Column(Integer, ForeignKey('contribution.pk'), primary_key=True)
    number = Column(Integer)
    published = Column(Date)
    toc = Column(Unicode)
    doi = Column(Unicode)

    def metalanguage_label(self, lang):
        style = self.jsondata['metalanguage_styles'].get(lang)
        style = "label label-{0}".format(style) if style else lang
        return HTML.span(lang, class_=style)

    def doi_link(self):
        if self.doi:
            return external_link(
                'https://doi.org/{0.doi}'.format(self), label='DOI: {0.doi}'.format(self))
        return ''


@implementer(interfaces.IUnit)
class Construction(CustomModelMixin, Unit):
    pk = Column(Integer, ForeignKey('unit.pk'), primary_key=True)
    contribution_pk = Column(Integer, ForeignKey('contribution.pk'))
    contribution = relationship(CrossgramData, backref='constructions')


@implementer(interfaces.IUnitParameter)
class CParameter(CustomModelMixin, UnitParameter):
    pk = Column(Integer, ForeignKey('unitparameter.pk'), primary_key=True)
    contribution_pk = Column(Integer, ForeignKey('contribution.pk'))
    contribution = relationship(CrossgramData, backref='cparameters')


@implementer(interfaces.IParameter)
class LParameter(CustomModelMixin, Parameter):
    pk = Column(Integer, ForeignKey('parameter.pk'), primary_key=True)
    contribution_pk = Column(Integer, ForeignKey('contribution.pk'))
    contribution = relationship(CrossgramData, backref='lparameters')


@implementer(interfaces.ISentence)
class Example(CustomModelMixin, Sentence):
    pk = Column(Integer, ForeignKey('sentence.pk'), primary_key=True)
    contribution_pk = Column(Integer, ForeignKey('contribution.pk'))
    contribution = relationship(CrossgramData, backref='examples')


class UnitValueReference(Base):

    unitvalue_pk = Column(Integer, ForeignKey('unitvalue.pk'))
    source_pk = Column(Integer, ForeignKey('source.pk'))
    unitvalue = relationship('UnitValue', backref='source_assocs')
    source = relationship('Source', backref='unitvalue_assocs')


class UnitValueSentence(Base):

    unitvalue_pk = Column(Integer, ForeignKey('unitvalue.pk'))
    sentence_pk = Column(Integer, ForeignKey('sentence.pk'))
    unitvalue = relationship('UnitValue', backref='sentence_assocs')
    sentence = relationship('Sentence', backref='unitvalue_assocs')


@implementer(interfaces.ISource)
class CrossgramDataSource(CustomModelMixin, Source):
    pk = Column(Integer, ForeignKey('source.pk'), primary_key=True)
    contribution_pk = Column(Integer, ForeignKey('contribution.pk'))
    contribution = relationship(CrossgramData, backref='sources')
