from functools import cached_property

import click

from ..client import ContractClient
from ..utils import token_path


class ContractMixin:
    @cached_property
    def contract(self):
        contract = self._client.contracts()[0]
        assert contract['ContractState'] == 'ACTIVE', 'Contract NOT active'
        return ContractClient(self._client, contract['Token'])


class TokenMixin:
    @cached_property
    def token(self):
        path = token_path()
        try:
            token = path.read_text()
        except FileNotFoundError:
            raise click.ClickException('Run `login` first')
        return token
