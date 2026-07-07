import click

from .. import client
from . import _mixins
from .cli import CLI


class Services(CLI.Command, _mixins.ContractMixin, _mixins.TokenMixin):
    """List available refund submission services."""

    def __call__(self):
        try:
            if not self.contract.validate_feature('REFUNDS_SUBMISSION'):
                raise click.ClickException('Refund submission not available')
            setup = self.contract.refunds_request_setup()
        except client.exceptions.ClientError as e:
            raise click.ClickException(str(e))

        for service in setup.services:
            click.echo(service.name)
