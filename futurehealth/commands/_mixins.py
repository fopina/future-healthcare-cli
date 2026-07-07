from dataclasses import dataclass
from functools import cached_property

import classyclick
import click

from ..client import Client, ContractClient
from ..utils import token_path


class ContractMixin:
    @cached_property
    def contract(self):
        contract = self.client.contracts()[0]
        assert contract['ContractState'] == 'ACTIVE', 'Contract NOT active'
        return ContractClient(self.client, contract['Token'])


@dataclass(init=False)
class TlsVerifyMixin:
    # Replace with classyclick.ContextMeta(..., default=True) if/when supported:
    # https://github.com/fopina/classyclick/issues/81
    class _DefaultContextMeta(classyclick.Context):
        default = True

        def __init__(self, key: str, **attrs):
            super().__init__(**attrs)
            self._ctx_meta_key = key

        def __call__(self, command):
            self.store_field_name(command)
            return self.click.decorators.pass_meta_key(self._ctx_meta_key, **self.attrs)(command)

    tls_verify: bool = _DefaultContextMeta('tls_verify')


class TokenMixin(TlsVerifyMixin):
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
        return Client(token=self.token, verify=self.tls_verify)
