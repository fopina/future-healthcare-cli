import click
import tomllib

from ..utils import config_path


def load_config() -> dict:
    path = config_path()
    if not path.exists():
        return {}
    with path.open('rb') as f:
        return tomllib.load(f)


@click.group(context_settings={'default_map': load_config()})
def cli():
    """CLI for Future Healthcare"""
