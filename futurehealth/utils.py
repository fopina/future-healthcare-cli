from pathlib import Path

from platformdirs import user_config_path

APP_NAME = 'future-healthcare-cli'
CONFIG_FILENAME = 'config.toml'
TOKEN_FILENAME = 'token.txt'


def config_path() -> Path:
    return user_config_path(APP_NAME) / CONFIG_FILENAME


def token_path() -> Path:
    return user_config_path(APP_NAME) / TOKEN_FILENAME
