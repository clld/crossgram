from pathlib import Path

from clld.web.assets import environment

import crossgram


environment.append_path(
    Path(crossgram.__file__).parent.joinpath('static').as_posix(),
    url='/crossgram:static/')
environment.load_path = list(reversed(environment.load_path))
