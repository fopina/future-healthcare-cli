from functools import cached_property
from pathlib import Path

import classyclick
import click

from ..client import Client
from . import _mixins
from .cli import cli


@classyclick.command(group=cli)
class Submit(_mixins.ContractMixin, _mixins.TokenMixin):
    person: str = classyclick.Option(
        '-p', help='Name of the insured person. If not specified or multiple matches, it will be prompted interactively'
    )
    service: str = classyclick.Option(
        '-s',
        help='Name of the service to request refund. If not specified or multiple matches, it will be prompted interactively',
    )

    _client = None

    def __call__(self):
        self._client = Client(token=self.token)
        assert self.contract.validate_feature('REFUNDS_SUBMISSION'), 'Refund submission not available'
        NIF = '505956985'
        building = self.contract.load_buildings(NIF)['buildings']
        assert len(building) == 1
        building = building[0]
        print(building['id'], building['name'])
        docs = self._client.files(Path('/Users/fopina/Downloads/FR131329-1.pdf'), is_invoice=True)
        print(docs['guid'])
        service = self.get_service()
        person = self.get_person()
        print(service['Id'], service['Name'])
        print(person['CardNumber'], person['Name'], person['FiscalNumber'], person['Email'])
        self.contract.multiple_refunds_requests(
            person['CardNumber'],
            service['Id'],
            NIF,
            'FR 1/31329',
            25,
            '2025-10-11',
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
