import tomllib

import classyclick

from ..utils import config_path


def load_config() -> dict:
    path = config_path()
    if not path.exists():
        return {}
    with path.open('rb') as f:
        return tomllib.load(f)


class CLI(classyclick.Group):
    """CLI for Future Healthcare"""

    __config__ = classyclick.Group.Config(context_settings={'default_map': load_config()})
