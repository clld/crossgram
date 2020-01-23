from clldutils.misc import slug

from pyglottolog import Glottolog


def make_glottocode_index(glottolog_path):
    glottolog_api = Glottolog(glottolog_path)
    index = GlottocodeIndex()
    index.build_index(glottolog_api)
    return index


class GlottocodeIndex:

    def __init__(self):
        self._iso639_index = {}
        self._name_index = {}

    def build_index(self, glottolog):
        # Note: This might take a bit (ca. 20s on my machine)
        for languoid in glottolog.languoids():
            self._iso639_index[languoid.iso] = languoid.id
            self._name_index[slug(languoid.name)] = languoid.id

    def add_glottocode(self, language_row):
        if language_row.get('Glottocode'):
            return language_row

        glottocode = self._iso639_index.get(language_row.get('ISO639P3code'))
        if not glottocode:
            name = slug(language_row.get('Name', ''))
            glottocode = self._name_index.get(name)
        if not glottocode:
            return language_row

        new_row = dict(language_row)
        new_row['Glottocode'] = glottocode
        return new_row
