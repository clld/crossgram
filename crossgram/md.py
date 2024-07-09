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
                'incollection',
                f'{req.dataset.id}-{ctx.id}',
                address=req.dataset.publisher_place,
                author=[
                    author.name
                    for author in chain(
                        ctx.primary_contributors,
                        ctx.secondary_contributors)],
                bootitle=req.dataset.name,
                editor=[
                    editor.contributor.name
                    for editor in req.dataset.editors],
                publisher=req.dataset.publisher_name,
                title=getattr(ctx, 'citation_name', str(ctx)),
                url=req.resource_url(ctx),
                year=str(ctx.original_year))
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
