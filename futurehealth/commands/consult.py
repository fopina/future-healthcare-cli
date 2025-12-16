import classyclick
import click

from ..client import Client
from ..utils import token_path
from . import _mixins
from .cli import cli


@classyclick.command(group=cli)
class Consult(_mixins.ContractMixin, _mixins.TokenMixin):
    person: str = classyclick.Option(
        '-p', help='Name of the insured person. If not specified or multiple matches, it will be prompted interactively'
    )
    service: str = classyclick.Option(
        '-s',
        help='Name of the service to request refund. If not specified or multiple matches, it will be prompted interactively',
    )

    _client = None

    def __call__(self):
        path = token_path()
        try:
            token = path.read_text()
        except FileNotFoundError:
            raise click.ClickException('Run `login` first')

        self._client = Client(token=token)
        assert self._client.validate_feature(self.contract, 'REFUNDS_CONSULT'), 'Refund consult not available'
        print(self._client.unified_refunds(self.contract))
