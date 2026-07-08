from pathlib import Path

import classyclick
import click

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
    errors_path: Path = classyclick.Option(
        help='Path to the cached Future Healthcare error details JSON file',
        show_default='errors.json next to --config',
    )
    locale: str = classyclick.Option(
        default=utils.locale(),
        help='Locale for translated Future Healthcare API error messages: pt-PT or en-US',
    )
    insecure: bool = classyclick.Option('-k', help='Disable TLS certificate verification')

    __config__ = classyclick.Group.Config(context_settings={'show_default': True})

    def __call__(self):
        self.load_config()
        self.token_path = utils.token_path(self.config, override=self.token_path)
        self.log_dir = utils.logs_path(self.config, override=self.log_dir)
        self.errors_path = utils.errors_path(self.config, override=self.errors_path)
        try:
            self.locale = utils.locale(override=self.locale)
        except ValueError as e:
            raise click.ClickException(str(e))
        self.ctx.meta['token_path'] = self.token_path
        self.ctx.meta['log_dir'] = self.log_dir
        self.ctx.meta['errors_path'] = self.errors_path
        self.ctx.meta['locale'] = self.locale
        self.ctx.meta['tls_verify'] = not self.insecure
