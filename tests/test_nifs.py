import unittest
from unittest.mock import MagicMock, patch

import click

from futurehealth.client.models import Building
from futurehealth.commands.nifs import Nifs


class TestNifsCommand(unittest.TestCase):
    def test_lists_buildings_for_nif(self):
        contract = MagicMock()
        contract.validate_feature.return_value = True
        contract.load_buildings.return_value = [
            Building(id='b1', name='Hospital A', address='123 Main St'),
            Building(id='b2', name='Hospital B', address='456 Oak St'),
        ]

        cmd = Nifs(nif='123456789')
        cmd.contract = contract

        with patch('futurehealth.commands.nifs.click.echo') as echo:
            cmd()

        contract.validate_feature.assert_called_once_with('REFUNDS_SUBMISSION')
        contract.load_buildings.assert_called_once_with('123456789')
        self.assertEqual(
            [call.args[0] for call in echo.call_args_list],
            [
                'Hospital A (123 Main St)',
                'Hospital B (456 Oak St)',
            ],
        )

    def test_rejects_invalid_nif_without_api_lookup(self):
        contract = MagicMock()
        contract.validate_feature.return_value = True

        cmd = Nifs(nif='invalid')
        cmd.contract = contract

        with self.assertRaisesRegex(click.ClickException, 'invalid is not a valid NIF'):
            cmd()

        contract.load_buildings.assert_not_called()
