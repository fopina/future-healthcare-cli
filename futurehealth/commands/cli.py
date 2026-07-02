from pathlib import Path

import classyclick

from .. import utils


class CLI(classyclick.helpers.ConfigFileMixin, classyclick.Group):
    """CLI for Future Healthcare"""

    CONFIG_EXAMPLE_PATH = Path(__file__).with_name('config.example.toml')

    token_path: Path = classyclick.Option(
        help='Path to the local login token file',
        show_default='token.txt next to --config',
    )
    log_dir: Path = classyclick.Option(
        help='Directory for submission logs and copied input files',
        show_default='logs next to --config',
    )

    __config__ = classyclick.Group.Config(context_settings={'show_default': True})

    def __call__(self):
        self.load_config()
        self.token_path = utils.token_path(self.config, override=self.token_path)
        self.log_dir = utils.logs_path(self.config, override=self.log_dir)
        self.ctx.meta['token_path'] = self.token_path
        self.ctx.meta['log_dir'] = self.log_dir
