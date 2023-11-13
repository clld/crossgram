from clld.web.adapters.geojson import GeoJsonParameter
from clld import interfaces


class GeoJsonLParameter(GeoJsonParameter):

    def feature_properties(self, ctx, req, valueset):
        # use language names as tool tips for parameters with a closed domain
        if getattr(ctx, 'domain', None):
            label = self.get_language(ctx, req, valueset).name
        else:
            label = ', '.join(v.name for v in valueset.values if v.name)
        return {
            'values': list(valueset.values),
            'label': label}


def includeme(config):
    config.register_adapter(
        GeoJsonLParameter, interfaces.IParameter, interfaces.IRepresentation)
