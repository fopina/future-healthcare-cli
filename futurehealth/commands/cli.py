from pathlib import Path

import classyclick


class CLI(classyclick.helpers.ConfigFileMixin, classyclick.Group):
    """CLI for Future Healthcare"""

    CONFIG_EXAMPLE_PATH = Path(__file__).with_name('config.example.toml')

    __config__ = classyclick.Group.Config(context_settings={'show_default': True})

    def __call__(self):
        self.load_config()
