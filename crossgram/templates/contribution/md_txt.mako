<%! from clld.web.util import doi %>${', '.join(c.name for c in list(ctx.primary_contributors))}${' (with ' + ', '.join(c.name for c in list(ctx.secondary_contributors)) + ')' if ctx.secondary_contributors else ''}. ${ctx.original_year}. ${getattr(ctx, 'citation_name', str(ctx))}.
In: ${request.dataset.formatted_editors()|n} (eds.),
${request.dataset.name}.
${request.dataset.publisher_place}: ${request.dataset.publisher_name}.
(Available online at ${request.resource_url(ctx)}, Accessed on ${h.datetime.date.today()}.)
