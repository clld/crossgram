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
)


@implementer(interfaces.IContribution)
class DataSetContrib(CustomModelMixin, Contribution):
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


class UnitValueSentence(Base):

    unitvalue_pk = Column(Integer, ForeignKey('unitvalue.pk'))
    sentence_pk = Column(Integer, ForeignKey('sentence.pk'))
    unitvalue = relationship('UnitValue', backref='sentence_assocs')
    sentence = relationship('Sentence', backref='unitvalue_assocs')
