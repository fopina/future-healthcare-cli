import logging
import shutil
from datetime import datetime
from functools import cached_property
from pathlib import Path

import classyclick
import click
from openai import OpenAI

from .. import utils
from ..client import Client
from ..client.models import Building
from ..utils import prompts
from ..utils.models import ReceiptData
from . import _mixins
from .cli import cli


@classyclick.command(group=cli)
class Submit(_mixins.ContractMixin, _mixins.TokenMixin):
    receipt_file: Path = classyclick.Argument()

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
    # TODO: currently, in venice.ai, this same prompt is cheaper with Vision than with text???
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

    _client = None

    def __call__(self):
        self.setup_logging()
        try:
            data = self.parse_receipt()

            self._client = Client(token=self.token)
            assert self.contract.validate_feature('REFUNDS_SUBMISSION'), 'Refund submission not available'
            building = self.get_building(data.business_nif)
            self.console_logger.info('Building selected: %s', building)
            docs = self._client.files(self.receipt_file, is_invoice=True)
            self.console_logger.info('Document created: %s', docs['guid'])
            service = self.get_service()
            self.console_logger.info('Service selected: %s - %s', service.id, service.name)
            person = self.get_person()
            self.console_logger.info('Person selected: %s - %s', person.card_number, person.name)
            return
            self.contract.multiple_refunds_requests(
                person.card_number,
                service.id,
                data.business_nif,
                data.invoice_number,
                data.total_amount,
                data.date,
                [docs['guid']],
                False,
                False,
                building['id'],
                person.email,
            )
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
            model = self.openai_model_text
            messages.append(
                {'role': 'user', 'content': [{'type': 'text', 'text': prompts.USER_TEXT_PROMPT}] + pdf_content}
            )
        else:
            model = self.openai_model_vision
            messages.append(
                {'role': 'user', 'content': [{'type': 'text', 'text': prompts.USER_VISION_PROMPT}] + pdf_content}
            )
        completion = client.chat.completions.create(model=model, messages=messages, max_completion_tokens=500)

        message = completion.choices[0].message.content
        self.console_logger.info(f'Parsed receipt details: {message}')
        data = ReceiptData(**utils.parse_json_from_model(message))
        self.console_logger.info(f'Parsing token usage: {completion.usage}')
        return data

    def setup_logging(self):
        # Set up logging directory and file copying
        logs_dir = utils.logs_path()
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Generate prefix based on YEARMMDD_HHMM format
        now = datetime.now()
        prefix = now.strftime('%Y%m%d_%H%M')

        # Copy input file to logs directory with prefix
        receipt_copy = logs_dir / f'{prefix}_{self.receipt_file.name}'
        shutil.copy2(self.receipt_file, receipt_copy)

        # Set up formatters
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

        # Create file-only logger
        self.file_logger = logging.getLogger(f'file_{prefix}')
        self.file_logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler(logs_dir / f'{prefix}.log')
        file_handler.setFormatter(formatter)
        self.file_logger.addHandler(file_handler)

        # Create file-and-console logger
        self.console_logger = logging.getLogger(f'console_{prefix}')
        self.console_logger.setLevel(logging.INFO)
        self.console_logger.addHandler(file_handler)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.console_logger.addHandler(console_handler)

        self.console_logger.info(f'Starting submission for file: {self.receipt_file}')
        self.console_logger.info(f'Receipt file copied to: {receipt_copy}')
        self.console_logger.info(f'Logging to: {logs_dir / f"{prefix}.log"}')

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

    def get_building(self, nif: str) -> Building:
        cands = self.contract.load_buildings(nif)
        if not cands:
            raise click.ClickException(f"No building found matching '{nif}'")
        if len(cands) == 1:
            return cands[0]

        choices = [f'{i + 1}. {cand.name} address {cand.address}' for i, cand in enumerate(cands)]
        click.secho(f'Multiple buildings found for {nif}:', fg='red')
        for choice in choices:
            click.echo(choice)

        while True:
            try:
                selection = click.prompt('Select your building/address number', type=int, default=1)
                if 1 <= selection <= len(cands):
                    return cands[selection - 1]
                else:
                    click.echo(f'Please enter a number between 1 and {len(cands)}')
            except click.Abort:
                raise click.ClickException('Building selection cancelled')
