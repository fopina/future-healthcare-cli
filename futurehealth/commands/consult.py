import classyclick
import click

from ..client import Client
from . import _mixins
from .cli import cli


@classyclick.command(group=cli)
class Consult(_mixins.ContractMixin, _mixins.TokenMixin):
    _client = None

    def __call__(self):
        self._client = Client(token=self.token)
        assert self._client.validate_feature(self.contract, 'REFUNDS_CONSULT'), 'Refund consult not available'
        page = 1
        while True:
            r = self._client.unified_refunds(self.contract, page=page)
            for refund in r['Refunds']:
                # https://clientes-vic.future-healthcare.net/services/refunds/consult/XXX/detail
                # XXX = refund["ProcessNr"]
                received = refund['Claims'][0]['TotalInsurer']
                if received:
                    received_str = click.style(received, fg='green')
                else:
                    received_str = click.style(received, fg='red')
                click.echo(
                    f'{refund["Claims"][0]["DateOfTreatment"]} ({refund["ExpenseDate"]})[{refund["Claims"][0]["ServiceName"]}] - {refund["PersonName"]} - {refund["Claims"][0]["TotalCoPayment"]} + {received_str} = {refund["TotalValue"]}'
                )
            if r['PaginationResult']['CurrentPage'] < r['PaginationResult']['TotalPages']:
                page += 1
            else:
                break
