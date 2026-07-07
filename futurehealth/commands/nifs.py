import classyclick
import click

from .. import client, utils
from ..client.models import Building
from . import _mixins
from .cli import CLI


def format_building(building: Building, index: int | None = None) -> str:
    prefix = f'{index}. ' if index is not None else ''
    address = f' ({building.address})' if building.address else ''
    return f'{prefix}{building.name}{address}'


def normalize_building_name(building_name: str | None) -> str | None:
    if not isinstance(building_name, str):
        return None
    building_name = building_name.strip()
    return building_name or None


def select_building(
    contract,
    nif: str,
    building_name: str | None = None,
    *,
    prompt_for_nif: bool = True,
    prompt_for_building: bool = True,
) -> tuple[Building, str]:
    building_name = normalize_building_name(building_name)
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

    return select_building_from_candidates(cands, nif, building_name, prompt=prompt_for_building), nif


def select_building_from_candidates(
    cands: list[Building],
    nif: str,
    building_name: str | None = None,
    *,
    prompt: bool = True,
) -> Building:
    building_name = normalize_building_name(building_name)
    if building_name is not None:
        matches = [cand for cand in cands if (cand.name or '').casefold() == building_name.casefold()]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise click.ClickException(f"No building found named '{building_name}' for {nif}")
        raise click.ClickException(f"Multiple buildings named '{building_name}' found for {nif}")

    if len(cands) == 1:
        return cands[0]

    click.secho(f'Multiple buildings found for {nif}:', fg='red')
    for i, cand in enumerate(cands, start=1):
        click.echo(format_building(cand, i))

    if not prompt:
        raise click.ClickException(
            f'Multiple buildings found for {nif}. Pass --building with one of the names above, or use --interactive.'
        )

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

        for building in buildings:
            click.echo(format_building(building))
