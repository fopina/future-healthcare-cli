import logging
import re
import shutil
from datetime import datetime
from functools import cached_property
from pathlib import Path

import classyclick
import click

from .. import client, utils
from ..client.models import Building
from ..utils.models import ReceiptData
from . import _mixins
from .cli import CLI
from .fetch_error_details import ensure_error_details_files, translated_api_error_message
from .nifs import select_building


class Submit(CLI.Command, _mixins.ContractMixin, _mixins.TokenMixin):
    """Submit an expense, providing the receipt and, optionally, other attachments such as prescription"""

    receipt_file: Path = classyclick.Argument()
    other_attachments: list[Path] = classyclick.Argument(nargs=-1, type=Path)
    business_nif: str = classyclick.Option(help='Business NIF from the receipt')
    invoice_number: str = classyclick.Option(help='Invoice or receipt number')
    total_amount: float = classyclick.Option(help='Total amount paid')
    date: str = classyclick.Option(help='Treatment/payment date from the receipt')

    person: str = classyclick.Option(
        '-p',
        help='Name of the insured person. Must resolve to exactly one person unless --interactive is used',
    )
    service: str = classyclick.Option(
        '-s',
        help='Name of the service to request refund. Must resolve to exactly one service unless --interactive is used',
    )
    building: str = classyclick.Option(
        help='Building name to select when multiple addresses are found; use only the name before the address shown by `nifs`'
    )
    debug: bool = classyclick.Option(help='Enable debug logging')
    interactive: bool = classyclick.Option('-i', help='Prompt to resolve ambiguous or missing selections')
    primary_entity: bool = classyclick.Option(
        help='Whether this expense was already partially covered by another entity'
    )

    def __call__(self):
        self.setup_logging()
        ensure_error_details_files()
        try:
            data = self.get_receipt_data()
            self.console_logger.info(f'Receipt data: {data}')

            assert self.contract.validate_feature('REFUNDS_SUBMISSION'), 'Refund submission not available'
            building, new_nif = self.get_building(data.business_nif)
            self.console_logger.info('Building selected: %s', building)
            if new_nif != data.business_nif:
                self.console_logger.info('NIF fixed from %s to %s', data.business_nif, new_nif)
                data.business_nif = new_nif

            docs = []
            docs.append(self.client.files(self.receipt_file, is_invoice=True)['guid'])
            self.console_logger.info('Document created: %s', docs[-1])
            for other in self.other_attachments or []:
                docs.append(self.client.files(other)['guid'])
                self.console_logger.info('Document created: %s', docs[-1])

            service = self.get_service()
            self.console_logger.info('Service selected: %s - %s', service.id, service.name)
            person = self.get_person()
            self.console_logger.info('Person selected: %s - %s', person.card_number, person.name)
            self.contract.multiple_refunds_requests(
                person.card_number,
                service.id,
                data.business_nif,
                data.invoice_number,
                data.total_amount,
                data.date,
                docs,
                self.primary_entity,
                False,
                building.id,
                person.email,
            )
        except client.exceptions.ClientAPIError as e:
            self.file_logger.exception('Failed to submit with exception')
            raise click.ClickException(translated_api_error_message(e) or str(e))
        except client.exceptions.ClientError as e:
            self.file_logger.exception('Failed to submit with exception')
            raise click.ClickException(str(e))
        except Exception:
            self.file_logger.exception('Failed to submit with exception')
            raise
        self.console_logger.info('Submission completed')

    def get_receipt_data(self):
        self.validate_required_receipt_fields()
        data = ReceiptData(
            business_nif=self.business_nif,
            invoice_number=self.invoice_number,
            total_amount=self.total_amount,
            date=self.date,
        )
        data.date = self.normalize_date(data.date)
        self.console_logger.debug(f'Using receipt data from CLI flags: {data}')
        return data

    def validate_required_receipt_fields(self):
        missing = [
            flag
            for flag, value in (
                ('--business-nif', self.business_nif),
                ('--invoice-number', self.invoice_number),
                ('--total-amount', self.total_amount),
                ('--date', self.date),
            )
            if value in (None, '')
        ]
        if missing:
            joined = ', '.join(missing)
            raise click.ClickException(
                f'Missing required receipt fields: {joined}. Gather them before calling this command and pass them '
                'explicitly.'
            )

    def normalize_date(self, value: str) -> str:
        # It's either YEAR MM DD or DD MM YEAR (no US format), easy to detect.
        date_parts = re.findall(r'\b(\d+)\b', value)
        if len(date_parts) < 3:
            raise click.ClickException(f'{value} does not seem to contain a full date')
        if len(date_parts[2]) == 4:
            date_parts.reverse()
        elif len(date_parts[0]) != 4:
            raise click.ClickException(f'{value} does not seem to contain full year')
        return '-'.join(date_parts[:3])

    def setup_logging(self):
        # Set up logging directory and file copying
        logs_dir = utils.logs_path()
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Generate prefix based on YEARMMDD_HHMM format
        now = datetime.now()
        prefix = now.strftime('%Y%m%d_%H%M')

        # Set up formatters
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

        # Create file-only logger
        self.file_logger = logging.getLogger(f'file_{prefix}')
        self.file_logger.setLevel(logging.DEBUG)
        file_handler = logging.FileHandler(logs_dir / f'{prefix}.log')
        file_handler.setFormatter(formatter)
        self.file_logger.addHandler(file_handler)

        # Create file-and-console logger
        self.console_logger = logging.getLogger(f'console_{prefix}')
        self.console_logger.setLevel(logging.DEBUG)
        self.console_logger.addHandler(file_handler)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        if not self.debug:
            console_handler.setLevel(logging.INFO)
        self.console_logger.addHandler(console_handler)

        self.console_logger.info(f'Logging to: {logs_dir / f"{prefix}.log"}')
        self.console_logger.debug(f'Starting submission for file: {self.receipt_file}')

        # Copy input files to logs directory with prefix
        files_to_copy = [('Invoice/receipt file', self.receipt_file)] + [
            ('Supporting attachment file', attachment) for attachment in self.other_attachments or []
        ]
        for file_label, file in files_to_copy:
            file_copy = logs_dir / f'{prefix}_{file.name}'
            shutil.copy2(file, file_copy)
            self.console_logger.debug('%s copied to: %s', file_label, file_copy)

    @cached_property
    def refunds_request_setup(self):
        return self.contract.refunds_request_setup()

    def get_service(self):
        cands = self.refunds_request_setup.services
        if self.service:
            ls = self.service.lower()
            cands = [service for service in cands if ls in service.name.lower()]

        if not cands:
            raise click.ClickException(f"No service found matching '{self.service}'")

        if len(cands) == 1:
            return cands[0]

        choices = [f'{i + 1}. {cand.name}' for i, cand in enumerate(cands)]
        click.secho('Multiple services found:', fg='red')
        for choice in choices:
            click.echo(choice)

        if not self.interactive:
            raise click.ClickException(
                'Multiple services found. Pass --service with a more specific value, or use --interactive.'
            )

        while True:
            try:
                selection = click.prompt('Select service number', type=int, default=1)
                if 1 <= selection <= len(cands):
                    return cands[selection - 1]
                else:
                    click.echo(f'Please enter a number between 1 and {len(cands)}')
            except click.Abort:
                raise click.ClickException('Service selection cancelled')

    def get_person(self):
        cands = self.refunds_request_setup.insured_persons
        if self.person:
            lp = self.person.lower()
            cands = [person for person in cands if lp in person.name.lower()]

        if not cands:
            raise click.ClickException(f"No person found matching '{self.person}'")
        if len(cands) == 1:
            return cands[0]

        choices = [f'{i + 1}. {cand.name}' for i, cand in enumerate(cands)]
        click.secho('Multiple persons found:', fg='red')
        for choice in choices:
            click.echo(choice)

        if not self.interactive:
            raise click.ClickException(
                'Multiple persons found. Pass --person with a more specific value, or use --interactive.'
            )

        while True:
            try:
                selection = click.prompt('Select person number', type=int, default=1)
                if 1 <= selection <= len(cands):
                    return cands[selection - 1]
                else:
                    click.echo(f'Please enter a number between 1 and {len(cands)}')
            except click.Abort:
                raise click.ClickException('Person selection cancelled')

    def get_building(self, nif: str) -> tuple[Building, str]:
        return select_building(
            self.contract,
            nif,
            self.building,
            prompt_for_nif=self.interactive,
            prompt_for_building=self.interactive,
        )
