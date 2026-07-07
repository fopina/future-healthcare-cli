import unittest
from unittest.mock import MagicMock, patch

import click

from futurehealth import client
from futurehealth.client import RefundsRequestSetupResponse
from futurehealth.client.models import Service
from futurehealth.commands.services import Services


class TestServices(unittest.TestCase):
    def test_services_lists_available_service_names(self):
        contract = MagicMock()
        contract.validate_feature.return_value = True
        contract.refunds_request_setup.return_value = RefundsRequestSetupResponse(
            services=[
                Service(Id=1, Name='Dentist', IsMandatoryInvoiceFile=True, IsMandatoryAditionalFile=False),
                Service(Id=2, Name='Ophthalmology', IsMandatoryInvoiceFile=True, IsMandatoryAditionalFile=True),
            ],
            insured_persons=[],
            other={},
        )

        cmd = Services()
        cmd.contract = contract

        with patch('futurehealth.commands.services.click.echo') as echo:
            cmd()

        contract.validate_feature.assert_called_once_with('REFUNDS_SUBMISSION')
        contract.refunds_request_setup.assert_called_once_with()
        echo.assert_any_call('Dentist')
        echo.assert_any_call('Ophthalmology')

    def test_services_rejects_unavailable_submission_feature(self):
        contract = MagicMock()
        contract.validate_feature.return_value = False

        cmd = Services()
        cmd.contract = contract

        with self.assertRaises(click.ClickException):
            cmd()

        contract.refunds_request_setup.assert_not_called()

    def test_services_wraps_client_errors(self):
        contract = MagicMock()
        contract.validate_feature.side_effect = client.exceptions.ClientError('nope')

        cmd = Services()
        cmd.contract = contract

        with self.assertRaises(click.ClickException) as exc:
            cmd()

        self.assertEqual(str(exc.exception), 'nope')
