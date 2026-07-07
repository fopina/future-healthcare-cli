from functools import cached_property

import click

from ..client import Client, ContractClient
from ..utils import locale, tls_verify, token_path


class ContractMixin:
    @cached_property
    def contract(self):
        contract = self.client.contracts()[0]
        assert contract['ContractState'] == 'ACTIVE', 'Contract NOT active'
        return ContractClient(self.client, contract['Token'])


class TokenMixin:
    @cached_property
    def token(self):
        path = token_path()
        try:
            token = path.read_text()
        except FileNotFoundError:
            raise click.ClickException('Run `login` first')
        return token

    @cached_property
    def client(self):
        client_kwargs = {}
        if not tls_verify():
            client_kwargs['verify'] = False
        return Client(token=self.token, language=locale(), **client_kwargs)
