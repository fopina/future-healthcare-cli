from functools import cached_property

import classyclick
import click

from ..client import Client
from ..utils import token_path
from .cli import cli


@classyclick.command(group=cli)
class Submit:
    person: str = classyclick.Option(
        '-p', help='Name of the insured person. If not specified or multiple matches, it will be prompted interactively'
    )
    service: str = classyclick.Option(
        '-s',
        help='Name of the service to request refund. If not specified or multiple matches, it will be prompted interactively',
    )

    _client = None

    def __call__(self):
        path = token_path()
        try:
            token = path.read_text()
        except FileNotFoundError:
            raise click.ClickException('Run `login` first')

        self._client = Client(token=token)

        service = self.get_service()
        person = self.get_person()
        print(service)
        print(person)

    @cached_property
    def contract(self):
        contract = self._client.contracts()[0]
        assert contract['ContractState'] == 'ACTIVE', 'Contract NOT active'
        assert self._client.validate_feature(contract['Token'], 'REFUNDS_SUBMISSION'), 'Refund submission not available'
        return contract['Token']

    @cached_property
    def refunds_request_setup(self):
        return self._client.refunds_request_setup(self.contract)

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
