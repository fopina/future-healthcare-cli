import classyclick
import click

from ..client import Client
from ..utils import token_path
from .cli import cli


@classyclick.command(group=cli)
class Submit:
    def __call__(self):
        path = token_path()
        try:
            token = path.read_text()
        except FileNotFoundError:
            raise click.ClickException('Run `login` first')

        c = Client(token=token)
        contract = c.contracts()[0]
        assert contract['ContractState'] == 'ACTIVE', 'Contract NOT active'
        contract = contract['Token']
        assert c.validate_feature(contract, 'REFUNDS_SUBMISSION'), 'Refund submission not available'

        print(c.refunds_request_setup(contract, 'x'))
