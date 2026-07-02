import datetime as dt

import classyclick
import click

from .. import client
from . import _mixins
from .cli import CLI


class Check(CLI.Command, _mixins.ContractMixin, _mixins.TokenMixin):
    limit: int = classyclick.Option(default=None, help='Maximum number of refunds to show')
    last_days: int = classyclick.Option(default=None, help='Only show refunds from the last N days')

    def __call__(self):
        self.validate_options()
        cutoff_date = self.cutoff_date
        shown = 0
        try:
            if not self.contract.validate_feature('REFUNDS_CONSULT'):
                raise click.ClickException('Refund check not available')
        except client.exceptions.ClientError as e:
            raise click.ClickException(str(e))
        page = 1
        while True:
            r = self.contract.unified_refunds(page_size=20, page=page)
            for refund in r.refunds or []:
                if cutoff_date and not self.is_within_cutoff(refund, cutoff_date):
                    return

                # web UI details: https://clientes-vic.future-healthcare.net/services/refunds/consult/XXX/detail
                # XXX = refund.process_nr
                self.show_refund(refund)
                shown += 1
                if self.limit and shown >= self.limit:
                    return
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

    @property
    def cutoff_date(self):
        if not self.last_days:
            return None
        return dt.date.today() - dt.timedelta(days=self.last_days)

    def validate_options(self):
        if self.limit is not None and self.limit <= 0:
            raise click.ClickException('--limit must be greater than 0')
        if self.last_days is not None and self.last_days <= 0:
            raise click.ClickException('--last-days must be greater than 0')

    def is_within_cutoff(self, refund, cutoff_date):
        expense_date = self.parse_refund_date(refund.expense_date)
        return expense_date >= cutoff_date

    def parse_refund_date(self, value):
        if not value:
            raise click.ClickException('Cannot apply --last-days to a refund without an expense date')

        date_value = str(value).split('T', 1)[0]
        for date_format in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
            try:
                return dt.datetime.strptime(date_value, date_format).date()
            except ValueError:
                pass
        raise click.ClickException(f'Cannot parse refund expense date: {value}')

    def show_refund(self, refund):
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
