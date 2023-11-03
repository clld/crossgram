"""\
Okay, so, you might be wondering what's going on here...

AFAICT the data tables on the front end *have* to correspond to
a sqlalchemy-mapped query object.  This means we cannot have a data
table that displays the data of a join table.

Buuuut that clashes with the way language names work.  Languages have
different names in different contributions.  But the Language class only
has one name -- the one assigned by Glottolog:

    | id       | name                    |
    |----------+-------------------------|
    | abcd1234 | Glottolog Language Name |

So, for contribution-specific data tables I need to join in the
contribution-specific names from a separate table:

    | language | contribution | custom_name |
    |----------+--------------+-------------|
    | abcd1234 | 12           | Other Name  |
    | abcd1234 | 13           | Alt. Name   |

Except I can't.  So, instead I denormalised that whole table into the
language table.  More concretely, the `BlockEncoder` object takes the
contribution-specific information and wraps it into a string as key-value
pairs separated by unicode block elements (less likely to clash with
anything).

    | id       | name                    | custom_names                 |
    |----------+-------------------------+------------------------------|
    | abcd1234 | Glottolog Language Name | █12▒Other Name█13▒Alt. Name█ |

And on the other end the data table contains `BlockDecoder` objects, which
parse the information back out of the string (or provide regex's/SQL LIKE
queries that the data tables can chuck at sqlalchemy).
"""

import re


class BlockEncoder:
    def __init__(self):
        self._assocs = {}

    def record_value(self, language_id, contribution_pk, value):
        if value is None:
            return
        value = value.replace('▒', '').replace('█', '').strip()
        if not value:
            return
        if language_id not in self._assocs:
            self._assocs[language_id] = []
        self._assocs[language_id].append((contribution_pk, value))

    def encode(self, language_id, default_value=None):
        value_str = '█'.join(
            '{}▒{}'.format(contrib, value)
            for contrib, value in self._assocs.get(language_id, ())
            if default_value is None
            or value != default_value)
        if value_str:
            return '█{}█'.format(value_str)
        else:
            return None


class BlockDecoder:
    def __init__(self, contribution_pk):
        self._contribution_pk = contribution_pk
        self.regex_get_value = '█{}▒([^█]*)█'.format(contribution_pk)
        self.sql_has_contrib = f'%█{self._contribution_pk}▒%'

    def regex_search_value(self, query_string):
        return r'.*█{}▒[^█]*{}[^█]*█.*'.format(
            self._contribution_pk,
            re.escape(query_string))

    def extract_value(self, value):
        if (val_match := re.search(self.regex_get_value, (value or ''))):
            return val_match.group(1)
        else:
            return ''

    def iter_values(self, value):
        for val_match in re.finditer('▒([^█]+)█', value or ''):
            if (val := val_match.group(1).strip()):
                yield val
