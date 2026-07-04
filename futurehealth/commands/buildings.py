import classyclick
import click

from .. import client, utils
from ..client.models import Building
from . import _mixins
from .cli import CLI


def format_building(building: Building, index: int | None = None) -> str:
    prefix = f'{index}. ' if index is not None else ''
    address = f' address {building.address}' if building.address else ''
    return f'{prefix}{building.name}{address}'


def normalize_address_number(address_number: int | None) -> int | None:
    return address_number if isinstance(address_number, int) else None


def select_building(
    contract,
    nif: str,
    address_number: int | None = None,
    *,
    prompt_for_nif: bool = True,
) -> tuple[Building, str]:
    address_number = normalize_address_number(address_number)
    while True:
        if not utils.validate_nif(nif):
            if not prompt_for_nif:
                raise click.ClickException(f'{nif} is not a valid NIF')
            nif = click.prompt(f'{nif} is not a valid NIF, enter correct one')
            continue

        cands = contract.load_buildings(nif)
        if cands:
            break

        if not prompt_for_nif:
            raise click.ClickException(f'{nif} has no buildings')
        nif = click.prompt(f'{nif} has no buildings, enter correct one')

    return select_building_from_candidates(cands, nif, address_number), nif


def select_building_from_candidates(cands: list[Building], nif: str, address_number: int | None = None) -> Building:
    address_number = normalize_address_number(address_number)
    if address_number is not None:
        if 1 <= address_number <= len(cands):
            return cands[address_number - 1]
        raise click.ClickException(f'--address-number must be between 1 and {len(cands)}')

    if len(cands) == 1:
        return cands[0]

    click.secho(f'Multiple buildings found for {nif}:', fg='red')
    for i, cand in enumerate(cands, start=1):
        click.echo(format_building(cand, i))

    while True:
        try:
            selection = click.prompt('Select your building/address number', type=int, default=1)
            if 1 <= selection <= len(cands):
                return cands[selection - 1]
            click.echo(f'Please enter a number between 1 and {len(cands)}')
        except click.Abort:
            raise click.ClickException('Building selection cancelled')


class Nifs(CLI.Command, _mixins.ContractMixin, _mixins.TokenMixin):
    """Look up refund submission buildings/addresses for a business NIF."""

    nif: str = classyclick.Argument()
    address_number: int = classyclick.Option(
        help='1-based building/address number to select without prompting when multiple addresses are found'
    )

    def __call__(self):
        try:
            if not self.contract.validate_feature('REFUNDS_SUBMISSION'):
                raise click.ClickException('Refund submission not available')
            if not utils.validate_nif(self.nif):
                raise click.ClickException(f'{self.nif} is not a valid NIF')
            buildings = self.contract.load_buildings(self.nif)
        except client.exceptions.ClientError as e:
            raise click.ClickException(str(e))

        if not buildings:
            raise click.ClickException(f'{self.nif} has no buildings')

        if normalize_address_number(self.address_number) is not None:
            building = select_building_from_candidates(buildings, self.nif, self.address_number)
            click.echo(format_building(building))
            return

        for i, building in enumerate(buildings, start=1):
            click.echo(format_building(building, i))
