import re

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
    Language,
    Parameter,
    DomainElement,
    Sentence,
    Source,
    Unit,
    UnitParameter,
    UnitDomainElement,
    UnitValue,
)
from clld.db.models.source import HasSourceNotNullMixin
from clld.web.util.helpers import external_link
from clld.web.util.htmllib import HTML
from clld_glottologfamily_plugin.models import HasFamilyMixin


@implementer(interfaces.ILanguage)
class Variety(CustomModelMixin, Language, HasFamilyMixin):
    pk = Column(Integer, ForeignKey('language.pk'), primary_key=True)
    glottolog_id = Column(Unicode)
    example_count = Column(Integer)
    custom_names = Column(Unicode)


@implementer(interfaces.IContribution)
class CrossgramData(CustomModelMixin, Contribution):
    pk = Column(Integer, ForeignKey('contribution.pk'), primary_key=True)
    number = Column(Integer)
    published = Column(Date)
    original_year = Column(Unicode)
    toc = Column(Unicode)
    doi = Column(Unicode)
    git_repo = Column(Unicode)

    def metalanguage_label(self, lang):
        style = self.jsondata['metalanguage_styles'].get(lang)
        style = "label label-{0}".format(style) if style else lang
        return HTML.span(lang, class_=style)

    def doi_link(self):
        if self.doi:
            return external_link(
                'https://doi.org/{0.doi}'.format(self), label='DOI: {0.doi}'.format(self))
        return ''

    def git_link(self):
        if self.git_repo:
            match = re.search(r'github\.com/([^/]*)/([^/]*)', self.git_repo)
            if match:
                label = 'Github: %s/%s' % match.groups()
            else:
                label = 'Git: {}'.format(self.git_repo)
            return external_link(self.git_repo, label=label)
        else:
            return ''


class ContributionLanguage(Base):

    __table_args__ = (UniqueConstraint('language_pk', 'contribution_pk'),)

    contribution_pk = Column(Integer, ForeignKey('contribution.pk'))
    language_pk = Column(Integer, ForeignKey('language.pk'))
    custom_language_name = Column(Unicode)
    contribution = relationship(Contribution, backref='language_assocs')
    language = relationship(Language, backref='contribution_assocs')


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
    language_count = Column(Integer)


@implementer(interfaces.IUnitDomainElement)
class CCode(CustomModelMixin, UnitDomainElement):
    pk = Column(Integer, ForeignKey('unitdomainelement.pk'), primary_key=True)
    language_count = Column(Integer)


@implementer(interfaces.IParameter)
class LParameter(CustomModelMixin, Parameter):
    pk = Column(Integer, ForeignKey('parameter.pk'), primary_key=True)
    contribution_pk = Column(Integer, ForeignKey('contribution.pk'))
    contribution = relationship(CrossgramData, backref='lparameters')
    language_count = Column(Integer)


@implementer(interfaces.IDomainElement)
class LCode(CustomModelMixin, DomainElement):
    pk = Column(Integer, ForeignKey('domainelement.pk'), primary_key=True)
    language_count = Column(Integer)


@implementer(interfaces.ISentence)
class Example(CustomModelMixin, Sentence):
    pk = Column(Integer, ForeignKey('sentence.pk'), primary_key=True)
    ord = Column(Integer)
    contribution_pk = Column(Integer, ForeignKey('contribution.pk'))
    contribution = relationship(CrossgramData, backref='examples')


class LanguageReference(Base, HasSourceNotNullMixin):

    __table_args__ = (UniqueConstraint('language_pk', 'source_pk', 'description'),)

    language_pk = Column(Integer, ForeignKey('language.pk'), nullable=False)
    language = relationship(Language, innerjoin=True, backref='references')


class UnitReference(Base, HasSourceNotNullMixin):

    __table_args__ = (UniqueConstraint('unit_pk', 'source_pk', 'description'),)

    unit_pk = Column(Integer, ForeignKey('unit.pk'), nullable=False)
    unit = relationship(Unit, innerjoin=True, backref="references")


class UnitSentence(Base):

    unit_pk = Column(Integer, ForeignKey('unit.pk'))
    sentence_pk = Column(Integer, ForeignKey('sentence.pk'))
    unit = relationship('Unit', backref='sentence_assocs')
    sentence = relationship('Sentence', backref='unit_assocs')


class UnitValueReference(Base, HasSourceNotNullMixin):

    __table_args__ = (UniqueConstraint('unitvalue_pk', 'source_pk', 'description'),)

    unitvalue_pk = Column(Integer, ForeignKey('unitvalue.pk'), nullable=False)
    unitvalue = relationship(UnitValue, innerjoin=True, backref="references")


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
