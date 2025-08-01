import re

from zope.interface import implementer
from sqlalchemy import (
    Column,
    Unicode,
    Integer,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    Date,
)
from sqlalchemy.orm import relationship

from clld import interfaces
from clld.db.meta import Base, CustomModelMixin
from clld.db.models.common import (
    Contribution,
    IdNameDescriptionMixin,
    Language,
    Parameter,
    DomainElement,
    ValueSet,
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

from crossgram.interfaces import ITopic


@implementer(interfaces.ILanguage)
class Variety(CustomModelMixin, Language, HasFamilyMixin):
    pk = Column(Integer, ForeignKey('language.pk'), primary_key=True)
    glottolog_id = Column(Unicode)
    example_count = Column(Integer)
    custom_names = Column(Unicode)
    source_comments = Column(Unicode)


@implementer(interfaces.IContribution)
class CrossgramData(CustomModelMixin, Contribution):
    pk = Column(Integer, ForeignKey('contribution.pk'), primary_key=True)
    number = Column(Integer)
    published = Column(Date)
    original_year = Column(Unicode)
    toc = Column(Unicode)
    doi = Column(Unicode)
    git_repo = Column(Unicode)
    version = Column(Unicode)

    def metalanguage_label(self, lang):
        style = self.jsondata['metalanguage_styles'].get(lang)
        style = f'label label-{style}' if style else lang
        return HTML.span(lang, class_=style)

    def doi_link(self):
        if self.doi:
            return external_link(
                f'https://doi.org/{self.doi}', label=f'DOI: {self.doi}')
        return ''

    def git_link(self):
        if self.git_repo:
            if (m := re.search(r'github\.com/([^/]*)/([^/]*)', self.git_repo)):
                org, repo = m.groups()
                label = f'Github: {org}/{repo}'
            else:
                label = f'Git: {self.git_repo}'
            return external_link(self.git_repo, label=label)
        else:
            return ''


class ContributionLanguage(Base):

    __table_args__ = (UniqueConstraint('language_pk', 'contribution_pk'),)

    contribution_pk = Column(Integer, ForeignKey('contribution.pk'))
    contribution = relationship(Contribution, backref='language_assocs')
    language_pk = Column(Integer, ForeignKey('language.pk'))
    language = relationship(Language, backref='contribution_assocs')
    custom_language_name = Column(Unicode)
    source_comment = Column(Unicode)


@implementer(interfaces.IUnit)
class Construction(CustomModelMixin, Unit):
    pk = Column(Integer, ForeignKey('unit.pk'), primary_key=True)
    contribution_pk = Column(Integer, ForeignKey('contribution.pk'))
    contribution = relationship(CrossgramData, backref='constructions')
    source_comment = Column(Unicode)


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


@implementer(interfaces.IUnitValue)
class CValue(CustomModelMixin, UnitValue):
    pk = Column(Integer, ForeignKey('unitvalue.pk'), primary_key=True)
    source_comment = Column(Unicode)


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


@implementer(interfaces.IValueSet)
class LValueSet(CustomModelMixin, ValueSet):
    pk = Column(Integer, ForeignKey('valueset.pk'), primary_key=True)
    source_comment = Column(Unicode)


@implementer(interfaces.ISentence)
class Example(CustomModelMixin, Sentence):
    pk = Column(Integer, ForeignKey('sentence.pk'), primary_key=True)
    number = Column(Integer)
    contribution_pk = Column(Integer, ForeignKey('contribution.pk'))
    contribution = relationship(CrossgramData, backref='examples')
    source_comment = Column(Unicode)


class LanguageReference(Base, HasSourceNotNullMixin):

    __table_args__ = (UniqueConstraint('language_pk', 'source_pk', 'description'),)

    language_pk = Column(Integer, ForeignKey('language.pk'), nullable=False)
    language = relationship(Language, innerjoin=True, backref='references')


@implementer(ITopic)
class Topic(Base, IdNameDescriptionMixin):
    pk = Column(Integer, primary_key=True)
    quotation = Column(Unicode)
    comment = Column(Unicode)
    grammacode = Column(Unicode)
    wikipedia_counterpart = Column(Unicode)
    wikipedia_url = Column(Unicode)
    sil_counterpart = Column(Unicode)
    sil_url = Column(Unicode)
    # TODO(johannes): remove when we move to showing *all* topics
    used = Column(Boolean, default=False)


class ParameterTopic(Base):
    parameter_pk = Column(Integer, ForeignKey('parameter.pk'))
    parameter = relationship(Parameter, backref='topic_assocs')
    topic_pk = Column(Integer, ForeignKey('topic.pk'))
    topic = relationship(Topic, backref='parameter_assocs')


class UnitParameterTopic(Base):
    unitparameter_pk = Column(Integer, ForeignKey('unitparameter.pk'))
    unitparameter = relationship(UnitParameter, backref='topic_assocs')
    topic_pk = Column(Integer, ForeignKey('topic.pk'))
    topic = relationship(Topic, backref='unitparameter_assocs')


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
    description = Column(Unicode)


@implementer(interfaces.ISource)
class CrossgramDataSource(CustomModelMixin, Source):
    pk = Column(Integer, ForeignKey('source.pk'), primary_key=True)
    contribution_pk = Column(Integer, ForeignKey('contribution.pk'))
    contribution = relationship(CrossgramData, backref='sources')
