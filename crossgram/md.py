from itertools import chain

from zope.interface import implementer

from clld import interfaces
from clld.web.adapters.md import MetadataFromRec as Base
from clld.lib import bibtex


class MetadataFromRec(Base):

    """Virtual base class deriving metadata from a bibtex record."""

    def rec(self, ctx, req):
        if interfaces.IContribution.providedBy(ctx):
            return bibtex.Record(
                'article',
                '{}-{}'.format(req.dataset.id, ctx.id),
                author = [
                    c.name
                    for c in chain(ctx.primary_contributors, ctx.secondary_contributors)],
                year=str(ctx.published.year),
                title=getattr(ctx, 'citation_name', str(ctx)),
                journal=req.dataset.description,
                volume=str(ctx.number),
                address=req.dataset.publisher_place,
                publisher=req.dataset.publisher_name,
                url=req.resource_url(ctx),
                doi=ctx.doi)
        else:
            return super().rec(ctx, req)


@implementer(interfaces.IRepresentation, interfaces.IMetadata)
class BibTex(MetadataFromRec):

    """Resource metadata as BibTex record."""

    name = 'BibTeX'
    __label__ = 'BibTeX'
    unapi = 'bibtex'
    extension = 'md.bib'
    mimetype = 'text/x-bibtex'

    def render(self, ctx, req):
        return str(self.rec(ctx, req))
