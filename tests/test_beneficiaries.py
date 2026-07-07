import unittest
from unittest.mock import MagicMock, patch

import click

from futurehealth import client
from futurehealth.client import RefundsRequestSetupResponse
from futurehealth.client.models import Person
from futurehealth.commands.beneficiaries import Beneficiaries


class TestBeneficiaries(unittest.TestCase):
    def test_beneficiaries_lists_names_and_numbers(self):
        contract = MagicMock()
        contract.validate_feature.return_value = True
        contract.refunds_request_setup.return_value = RefundsRequestSetupResponse(
            services=[],
            insured_persons=[
                Person(CardNumber='123456789', Name='Alice Example', Email='alice@example.test'),
                Person(CardNumber='987654321', Name='Bob Example', Email='bob@example.test'),
            ],
            other={},
        )

        cmd = Beneficiaries()
        cmd.contract = contract

        with patch('futurehealth.commands.beneficiaries.click.echo') as echo:
            cmd()

        contract.validate_feature.assert_called_once_with('REFUNDS_SUBMISSION')
        contract.refunds_request_setup.assert_called_once_with()
        echo.assert_any_call('Alice Example - 123456789')
        echo.assert_any_call('Bob Example - 987654321')

    def test_beneficiaries_rejects_unavailable_submission_feature(self):
        contract = MagicMock()
        contract.validate_feature.return_value = False

        cmd = Beneficiaries()
        cmd.contract = contract

        with self.assertRaises(click.ClickException):
            cmd()

        contract.refunds_request_setup.assert_not_called()

    def test_beneficiaries_wraps_client_errors(self):
        contract = MagicMock()
        contract.validate_feature.side_effect = client.exceptions.ClientError('nope')

        cmd = Beneficiaries()
        cmd.contract = contract

        with self.assertRaises(click.ClickException) as exc:
            cmd()

        self.assertEqual(str(exc.exception), 'nope')
