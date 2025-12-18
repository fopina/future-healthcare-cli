import logging
import re
import shutil
from datetime import datetime
from functools import cached_property
from pathlib import Path

import classyclick
import click
from openai import OpenAI

from .. import client, utils
from ..client.models import Building
from ..utils import prompts
from ..utils.models import ReceiptData
from . import _mixins
from .cli import cli


@classyclick.command(group=cli)
class Submit(_mixins.ContractMixin, _mixins.TokenMixin):
    """Submit an expense, providing the receipt and, optionally, other attachments such as prescription"""

    receipt_file: Path = classyclick.Argument()
    other_attachments: list[Path] = classyclick.Argument(nargs=-1, type=Path)

    person: str = classyclick.Option(
        '-p', help='Name of the insured person. If not specified or multiple matches, it will be prompted interactively'
    )
    service: str = classyclick.Option(
        '-s',
        help='Name of the service to request refund. If not specified or multiple matches, it will be prompted interactively',
    )
    openai_api_key: str = classyclick.Option(
        help='API key to access the OpenAI-compatible service to read the receipts'
    )
    openai_api_url: str = classyclick.Option(
        default='https://api.venice.ai/api/v1',
        help='API base url of the OpenAI-compatible service to read the receipts',
    )
    # currently, in venice.ai, this same prompt is cheaper with Vision than with text???
    # same model used for both as it is indeed currently the cheapest for anything in venice.ai
    openai_model_vision: str = classyclick.Option(
        default='google-gemma-3-27b-it', help='Model to use when receipts are in image format or scanned PDF'
    )
    openai_model_text: str = classyclick.Option(
        default='google-gemma-3-27b-it', help='Model to use when receipts are in text-based PDF'
    )
    force_vision: bool = classyclick.Option(
        help='If receipt is not an image, convert it anyway - only useful if Vision model is cheaper or performs better...'
    )
    vision_dpi: int = classyclick.Option(
        default=200,
        help='When converting PDF to image, use this DPI. Higher DPI should yield higher cost but more accuracy.',
    )
    debug: bool = classyclick.Option(help='Enable debug logging')
    primary_entity: bool = classyclick.Option(
        help='Whether this expense was already partially covered by another entity'
    )

    _client = None

    def __call__(self):
        self.setup_logging()
        try:
            data = self.parse_receipt()
            self.review_data(data)
            self.console_logger.info(f'Parsed data after review: {data}')

            self._client = client.Client(token=self.token)
            assert self.contract.validate_feature('REFUNDS_SUBMISSION'), 'Refund submission not available'
            building, new_nif = self.get_building(data.business_nif)
            self.console_logger.info('Building selected: %s', building)
            if new_nif != data.business_nif:
                self.console_logger.info('NIF fixed from %s to %s', data.business_nif, new_nif)
                data.business_nif = new_nif

            docs = []
            docs.append(self._client.files(self.receipt_file, is_invoice=True)['guid'])
            self.console_logger.info('Document created: %s', docs[-1])
            for other in self.other_attachments or []:
                docs.append(self._client.files(other)['guid'])
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
        except client.exceptions.ClientError as e:
            self.file_logger.exception('Failed to submit with exception')
            raise click.ClickException(str(e))
        except Exception:
            self.file_logger.exception('Failed to submit with exception')
            raise
        self.console_logger.info('Submission completed')

    def parse_receipt(self):
        pdf_content = utils.read_pdf(self.receipt_file, force_vision=self.force_vision, dpi=self.vision_dpi)

        client = OpenAI(
            api_key=self.openai_api_key,
            base_url=self.openai_api_url,
        )

        messages = []
        if prompts.SYSTEM_PROMPT:
            messages.append({'role': 'system', 'content': prompts.SYSTEM_PROMPT})
        if pdf_content[0]['type'] == 'text':
            self.console_logger.debug('Using text model - %s', self.openai_model_text)
            model = self.openai_model_text
            messages.append(
                {'role': 'user', 'content': [{'type': 'text', 'text': prompts.USER_TEXT_PROMPT}] + pdf_content}
            )
        else:
            self.console_logger.debug('Using vision model - %s', self.openai_model_vision)
            model = self.openai_model_vision
            messages.append(
                {'role': 'user', 'content': [{'type': 'text', 'text': prompts.USER_VISION_PROMPT}] + pdf_content}
            )
        completion = client.chat.completions.create(model=model, messages=messages, max_completion_tokens=500)

        message = completion.choices[0].message.content
        self.console_logger.debug(f'Parsed receipt details: {message}')
        data = ReceiptData(**utils.parse_json_from_model(message))
        # convert date - not done in LLM as testing shown issues with proper format conversion
        # it's either YEAR MM DD or DD MM YEAR (no US format), easy to detect
        date_parts = re.findall(r'\b(\d+)\b', data.date)
        if len(date_parts[2]) == 4:
            date_parts.reverse()
        elif len(date_parts[0]) != 4:
            raise click.ClickException(f'{data.date} does not seem to contain full year')
        data.date = '-'.join(date_parts)
        self.console_logger.debug(f'Tokens used: {completion.usage}')
        self.console_logger.debug(f'Parsed data (before review): {data}')
        return data

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
        for file in [self.receipt_file] + list(self.other_attachments):
            file_copy = logs_dir / f'{prefix}_{file.name}'
            shutil.copy2(file, file_copy)
            self.console_logger.debug(f'Receipt file copied to: {file_copy}')

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
        while True:
            if not utils.validate_nif(nif):
                nif = click.prompt(f'{nif} is not a valid NIF, enter correct one')
                continue
            cands = self.contract.load_buildings(nif)
            if cands:
                break
            nif = click.prompt(f'{nif} has no buildings, enter correct one')

        if len(cands) == 1:
            return cands[0], nif

        choices = [f'{i + 1}. {cand.name} address {cand.address}' for i, cand in enumerate(cands)]
        click.secho(f'Multiple buildings found for {nif}:', fg='red')
        for choice in choices:
            click.echo(choice)

        while True:
            try:
                selection = click.prompt('Select your building/address number', type=int, default=1)
                if 1 <= selection <= len(cands):
                    return cands[selection - 1], nif
                else:
                    click.echo(f'Please enter a number between 1 and {len(cands)}')
            except click.Abort:
                raise click.ClickException('Building selection cancelled')

    def review_data(self, data: ReceiptData):
        click.secho('Review the extract data and choose any to fix:', fg='red')
        fields = list(data.__class__.model_fields)
        click.echo('0. All good!')
        for i, field in enumerate(fields):
            click.echo(f'{i + 1}. {field} = {getattr(data, field)}')
        while True:
            try:
                selection = click.prompt('Select the field you want to change', type=int, default=0)
                if selection == 0:
                    return
                if selection > len(fields):
                    click.echo(f'Please enter a number between 0 and {len(fields)}')
                else:
                    field = fields[selection - 1]
                    cur_val = getattr(data, field) or ''
                    new_val = click.prompt(f'New value for {field}', type=str, default=str(cur_val))
                    setattr(data, field, new_val)
                    new_val = getattr(data, field)
                    click.echo(f'{field} updated to {new_val}')
            except click.Abort:
                raise click.ClickException('Review cancelled')
