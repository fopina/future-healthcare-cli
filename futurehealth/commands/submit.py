from functools import cached_property
from pathlib import Path

import classyclick
import click
from openai import OpenAI

from .. import utils
from ..client import Client
from ..utils import prompts
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
        print(f'Details: {message}')
        data = utils.parse_json_from_model(message)
        print(f'Usage: {completion.usage}')

        self._client = Client(token=self.token)
        assert self.contract.validate_feature('REFUNDS_SUBMISSION'), 'Refund submission not available'
        building = self.get_building(data['business_nif'])
        print(building['id'], building['name'])
        docs = self._client.files(self.receipt_file, is_invoice=True)
        print(docs['guid'])
        service = self.get_service()
        person = self.get_person()
        print(service['Id'], service['Name'])
        print(person['CardNumber'], person['Name'], person['FiscalNumber'], person['Email'])
        self.contract.multiple_refunds_requests(
            person['CardNumber'],
            service['Id'],
            data['business_nif'],
            data['invoice_number'],
            data['total_amount'],
            data['date'],
            [docs['guid']],
            False,
            False,
            building['id'],
            person['Email'],
        )

    @cached_property
    def refunds_request_setup(self):
        return self.contract.refunds_request_setup()

    def get_service(self):
        cands = self.refunds_request_setup['Services']
        if self.service:
            ls = self.service.lower()
            cands = [service for service in cands if ls in service['Name'].lower()]

        if not cands:
            raise click.ClickException(f"No service found matching '{self.service}'")

        if len(cands) == 1:
            return cands[0]

        choices = [f'{i + 1}. {cand["Name"]}' for i, cand in enumerate(cands)]
        click.echo('Multiple services found:')
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
        cands = self.refunds_request_setup['InsuredPersons']
        if self.person:
            lp = self.person.lower()
            cands = [person for person in cands if lp in person['Name'].lower()]

        if not cands:
            raise click.ClickException(f"No person found matching '{self.person}'")
        if len(cands) == 1:
            return cands[0]

        choices = [f'{i + 1}. {cand["Name"]}' for i, cand in enumerate(cands)]
        click.echo('Multiple persons found:')
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

    def get_building(self, nif: str):
        cands = self.contract.load_buildings(nif)['buildings']
        if not cands:
            raise click.ClickException(f"No building found matching '{nif}'")
        if len(cands) == 1:
            return cands[0]

        choices = [f'{i + 1}. {cand}' for i, cand in enumerate(cands)]
        click.echo(f'Multiple buildings found for {nif}:')
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
