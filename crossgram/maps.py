from clld.web.util import helpers
from clld.web import maps


class LParameterMap(maps.Map):

    def get_layers(self):
        param = self.ctx
        if param.domain:
            for domainelement in param.domain:
                de_query = {
                    'domainelement': str(domainelement.id),
                    **self.req.query_params}
                data = self.req.resource_url(
                    param, ext='geojson', _query=de_query)
                marker = helpers.map_marker_img(
                    self.req, domainelement, marker=self.map_marker)
                yield maps.Layer(
                    domainelement.id,
                    domainelement.name,
                    data,
                    marker=marker)
        else:
            data = self.req.resource_url(param, ext='geojson')
            yield maps.Layer(param.id, param.name, data)

    def get_options(self):
        param = self.ctx
        options = {
            'resize_direction': 's',
            'info_query': {'parameter': param.pk},
            'hash': True,
        }
        # if not param.domain:
        #     options['show_labels'] = True
        return options


def includeme(config):
    config.register_map('parameter', LParameterMap)
