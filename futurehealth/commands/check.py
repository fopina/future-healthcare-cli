import click

from . import _mixins
from .cli import CLI


class Check(CLI.Command, _mixins.ContractMixin, _mixins.TokenMixin):
    def __call__(self):
        assert self.contract.validate_feature('REFUNDS_CONSULT'), 'Refund check not available'
        page = 1
        while True:
            r = self.contract.unified_refunds(page_size=20, page=page)
            for refund in r.refunds:
                # web UI details: https://clientes-vic.future-healthcare.net/services/refunds/consult/XXX/detail
                # XXX = refund.process_nr
                claim = refund.claims[0] if refund.claims else None
                received = claim.total_insurer if claim else None
                if received:
                    received_str = click.style(received, fg='green')
                else:
                    received_str = click.style(received, fg='red')
                if claim:
                    click.echo(
                        f'{claim.date_of_treatment} ({refund.expense_date})[{claim.service_name}] - {refund.person_name} - {claim.total_copayment} + {received_str} = {refund.total_value}'
                    )
                else:
                    click.echo(
                        f'{refund.expense_date} [{refund.type}] - {refund.person_name} - {refund.status} = {refund.total_value}'
                    )
            pagination = r.pagination_result
            if (
                pagination
                and pagination.current_page
                and pagination.total_pages
                and pagination.current_page < pagination.total_pages
            ):
                page += 1
            else:
                break
