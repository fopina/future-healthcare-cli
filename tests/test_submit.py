import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import click

from futurehealth.client import exceptions
from futurehealth.client.models import Building, Person, Service
from futurehealth.commands.submit import Submit


class TestSubmitCommand(unittest.TestCase):
    """Test cases for the Submit command."""

    def test_submit_initialization(self):
        """Test Submit command initialization with options."""
        submit = Submit(
            receipt_file=Path('test.pdf'),
            business_nif='123456789',
            invoice_number='INV-1',
            total_amount=12.5,
            date='2023-01-01',
            person='John',
            service='Medical',
            debug=True,
        )

        self.assertEqual(submit.receipt_file, Path('test.pdf'))
        self.assertEqual(submit.business_nif, '123456789')
        self.assertEqual(submit.invoice_number, 'INV-1')
        self.assertEqual(submit.total_amount, 12.5)
        self.assertEqual(submit.date, '2023-01-01')
        self.assertEqual(submit.person, 'John')
        self.assertEqual(submit.service, 'Medical')
        self.assertTrue(submit.debug)
        self.assertFalse(submit.interactive)

    @patch('futurehealth.commands.submit.Submit.setup_logging')
    @patch('futurehealth.commands.submit.Submit.get_building')
    @patch('futurehealth.commands.submit.Submit.get_service')
    @patch('futurehealth.commands.submit.Submit.get_person')
    @patch('futurehealth.commands.submit.ensure_error_details_files')
    @patch('futurehealth.commands._mixins.Client')
    @patch('futurehealth.client.ContractClient')
    def test_submit_full_flow(
        self,
        mock_contract_client,
        mock_client_class,
        mock_ensure_error_details,
        mock_get_person,
        mock_get_service,
        mock_get_building,
        mock_setup_logging,
    ):
        """Test the complete submit workflow."""
        # Setup mocks
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.files.return_value = {'guid': 'file_guid'}

        mock_contract = MagicMock()
        mock_contract.validate_feature.return_value = True
        mock_contract.multiple_refunds_requests.return_value = None
        mock_contract_client.return_value = mock_contract

        mock_building = Building(id='building_123', name='Hospital A', address='123 Main St')
        mock_get_building.return_value = (mock_building, '123456789')

        mock_service = Service(id=1, name='Medical Service', mantory_invoice_file=True, mantory_additional_file=False)
        mock_get_service.return_value = mock_service

        mock_person = Person(card_number='123456789', name='John Doe', email='john@example.com')
        mock_get_person.return_value = mock_person

        # Create submit command
        submit = Submit(
            receipt_file=Path('test.pdf'),
            business_nif='123456789',
            invoice_number='INV001',
            total_amount=100.50,
            date='2023-01-01',
        )
        submit.contract = mock_contract
        submit.file_logger = MagicMock()
        submit.console_logger = MagicMock()
        submit.token = 'test_token'  # Mock token to avoid file access

        # Execute
        submit()

        # Verify calls
        mock_setup_logging.assert_called_once()
        mock_ensure_error_details.assert_called_once_with(tls_verify=True)
        mock_client_class.assert_called_once()
        mock_contract.validate_feature.assert_called_once_with('REFUNDS_SUBMISSION')
        mock_get_building.assert_called_once_with('123456789')
        mock_client.files.assert_called_once()
        mock_get_service.assert_called_once()
        mock_get_person.assert_called_once()
        mock_contract.multiple_refunds_requests.assert_called_once_with(
            '123456789',  # person.card_number
            1,  # service.id
            '123456789',  # data.business_nif
            'INV001',  # data.invoice_number
            100.50,  # data.total_amount
            '2023-01-01',  # data.date
            ['file_guid'],  # docs guid
            False,  # param
            False,  # param
            'building_123',  # building.id
            'john@example.com',  # person.email
        )

    @patch('futurehealth.commands.submit.Submit.setup_logging')
    @patch('futurehealth.commands.submit.ensure_error_details_files')
    @patch('futurehealth.commands._mixins.Client')
    def test_submit_feature_not_available(self, mock_client_class, mock_ensure_error_details, mock_setup_logging):
        """Test submit when REFUNDS_SUBMISSION feature is not available."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_contract = MagicMock()
        mock_contract.validate_feature.return_value = False

        submit = Submit(
            receipt_file=Path('test.pdf'),
            business_nif='1',
            invoice_number='1',
            total_amount=1,
            date='2023-01-01',
        )
        submit.contract = mock_contract
        submit.file_logger = MagicMock()
        submit.console_logger = MagicMock()
        submit.token = 'test_token'  # Mock token to avoid file access

        with self.assertRaises(AssertionError):
            submit()

        mock_ensure_error_details.assert_called_once_with(tls_verify=True)

    @patch('futurehealth.commands.submit.Submit.setup_logging')
    @patch('futurehealth.commands.submit.ensure_error_details_files')
    @patch('futurehealth.commands._mixins.Client')
    def test_submit_requires_receipt_fields(self, mock_client_class, mock_ensure_error_details, mock_setup_logging):
        """Test submit validates required CLI fields."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_contract = MagicMock()
        mock_contract.validate_feature.return_value = True

        submit = Submit(receipt_file=Path('test.pdf'))
        submit.contract = mock_contract
        submit.file_logger = MagicMock()
        submit.console_logger = MagicMock()
        submit.token = 'test_token'
        submit.business_nif = None
        submit.invoice_number = None
        submit.total_amount = None
        submit.date = None

        with self.assertRaisesRegex(
            click.ClickException,
            r'Missing required receipt fields: --business-nif, --invoice-number, --total-amount, --date',
        ):
            submit()

        mock_setup_logging.assert_called_once_with()
        mock_ensure_error_details.assert_called_once_with(tls_verify=True)

    @patch('futurehealth.commands.submit.Submit.setup_logging')
    @patch('futurehealth.commands.submit.translated_api_error_message')
    @patch('futurehealth.commands.submit.ensure_error_details_files')
    def test_submit_translates_api_errors(self, mock_ensure_error_details, mock_translate, mock_setup_logging):
        """Test submit translates structured API errors when presenting them."""
        error = exceptions.ClientAPIError(
            {
                'resultCode': -108,
                'resultMessage': 'Validation failed',
                'resultCodeDetail': 'error.api.missing_request_data',
            }
        )
        mock_translate.return_value = 'Missing request data'

        mock_contract = MagicMock()
        mock_contract.validate_feature.side_effect = error

        submit = Submit(
            receipt_file=Path('test.pdf'),
            business_nif='1',
            invoice_number='1',
            total_amount=1,
            date='2023-01-01',
        )
        submit.contract = mock_contract
        submit.file_logger = MagicMock()
        submit.console_logger = MagicMock()

        with self.assertRaisesRegex(click.ClickException, 'Missing request data'):
            submit()

        mock_setup_logging.assert_called_once_with()
        mock_ensure_error_details.assert_called_once_with(tls_verify=True)
        mock_translate.assert_called_once_with(error)

    def test_setup_logging_labels_copied_input_files(self):
        """Test setup_logging labels invoice and attachment copies clearly."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            invoice = tmp_path / 'invoice.pdf'
            prescription = tmp_path / 'prescription.pdf'
            logs_dir = tmp_path / 'logs'
            invoice.write_text('invoice')
            prescription.write_text('prescription')

            submit = Submit(receipt_file=invoice, other_attachments=[prescription], debug=True)

            try:
                with patch('futurehealth.commands.submit.utils.logs_path', return_value=logs_dir):
                    submit.setup_logging()

                log_text = ''.join(log_file.read_text() for log_file in logs_dir.glob('*.log'))
                self.assertIn('Invoice/receipt file copied to:', log_text)
                self.assertIn('Supporting attachment file copied to:', log_text)
                self.assertIn('_invoice.pdf', log_text)
                self.assertIn('_prescription.pdf', log_text)
            finally:
                for logger in (submit.file_logger, submit.console_logger):
                    for handler in list(logger.handlers):
                        logger.removeHandler(handler)
                        handler.close()

    def test_get_receipt_data_uses_flags_by_default(self):
        """Test receipt data comes from CLI flags."""
        submit = Submit(
            receipt_file=Path('test.pdf'),
            business_nif='123456789',
            invoice_number='INV001',
            total_amount='100.50',
            date='01/01/2023',
        )
        submit.console_logger = MagicMock()

        result = submit.get_receipt_data()

        self.assertEqual(result.business_nif, '123456789')
        self.assertEqual(result.invoice_number, 'INV001')
        self.assertEqual(result.total_amount, 100.50)
        self.assertEqual(result.date, '2023-01-01')

    def test_get_service_single_match(self):
        """Test get_service with single match."""
        # FIXME: service=None should not be needed @ classyclick
        submit = Submit(receipt_file=Path('test.pdf'), service=None)

        # Mock refunds_request_setup
        mock_setup = MagicMock()
        mock_setup.services = [
            Service(id=1, name='Medical Service', mantory_invoice_file=True, mantory_additional_file=False)
        ]
        submit.refunds_request_setup = mock_setup

        result = submit.get_service()

        self.assertEqual(result.id, 1)
        self.assertEqual(result.name, 'Medical Service')

    def test_get_service_multiple_matches_interactive(self):
        """Test get_service with multiple matches - interactive selection."""
        submit = Submit(receipt_file=Path('test.pdf'), service=None, interactive=True)

        # Mock refunds_request_setup
        mock_setup = MagicMock()
        mock_setup.services = [
            Service(Id=1, Name='Medical Service A', IsMandatoryInvoiceFile=True, IsMandatoryAditionalFile=False),
            Service(Id=2, Name='Medical Service B', IsMandatoryInvoiceFile=True, IsMandatoryAditionalFile=False),
        ]
        submit.refunds_request_setup = mock_setup

        with patch('click.prompt', return_value=1):
            result = submit.get_service()

        self.assertEqual(result.id, 1)
        self.assertEqual(result.name, 'Medical Service A')

    def test_get_service_multiple_matches_non_interactive(self):
        """Test get_service with multiple matches fails without prompting by default."""
        submit = Submit(receipt_file=Path('test.pdf'), service=None)

        mock_setup = MagicMock()
        mock_setup.services = [
            Service(Id=1, Name='Medical Service A', IsMandatoryInvoiceFile=True, IsMandatoryAditionalFile=False),
            Service(Id=2, Name='Medical Service B', IsMandatoryInvoiceFile=True, IsMandatoryAditionalFile=False),
        ]
        submit.refunds_request_setup = mock_setup

        with patch('click.prompt') as mock_prompt:
            with self.assertRaisesRegex(click.ClickException, 'Multiple services found'):
                submit.get_service()

        mock_prompt.assert_not_called()

    def test_get_service_no_matches(self):
        """Test get_service with no matches."""
        submit = Submit(receipt_file=Path('test.pdf'))
        submit.service = 'NonExistent'

        # Mock refunds_request_setup
        mock_setup = MagicMock()
        mock_setup.services = [
            Service(Id=1, Name='Medical Service', IsMandatoryInvoiceFile=True, IsMandatoryAditionalFile=False)
        ]
        submit.refunds_request_setup = mock_setup

        with self.assertRaises(Exception):  # ClickException
            submit.get_service()

    def test_get_person_single_match(self):
        """Test get_person with single match."""
        submit = Submit(receipt_file=Path('test.pdf'), person=None)

        # Mock refunds_request_setup
        mock_setup = MagicMock()
        mock_setup.insured_persons = [Person(CardNumber='123456789', Name='John Doe', Email='john@example.com')]
        submit.refunds_request_setup = mock_setup

        result = submit.get_person()

        self.assertEqual(result.card_number, '123456789')
        self.assertEqual(result.name, 'John Doe')

    def test_get_person_multiple_matches_interactive(self):
        """Test get_person with multiple matches - interactive selection."""
        submit = Submit(receipt_file=Path('test.pdf'), person=None, interactive=True)

        # Mock refunds_request_setup
        mock_setup = MagicMock()
        mock_setup.insured_persons = [
            Person(CardNumber='123456789', Name='John Doe', Email='john@example.com'),
            Person(CardNumber='987654321', Name='Jane Smith', Email='jane@example.com'),
        ]
        submit.refunds_request_setup = mock_setup

        with patch('click.prompt', return_value=2):
            result = submit.get_person()

        self.assertEqual(result.card_number, '987654321')
        self.assertEqual(result.name, 'Jane Smith')

    def test_get_person_multiple_matches_non_interactive(self):
        """Test get_person with multiple matches fails without prompting by default."""
        submit = Submit(receipt_file=Path('test.pdf'), person=None)

        mock_setup = MagicMock()
        mock_setup.insured_persons = [
            Person(CardNumber='123456789', Name='John Doe', Email='john@example.com'),
            Person(CardNumber='987654321', Name='Jane Smith', Email='jane@example.com'),
        ]
        submit.refunds_request_setup = mock_setup

        with patch('click.prompt') as mock_prompt:
            with self.assertRaisesRegex(click.ClickException, 'Multiple persons found'):
                submit.get_person()

        mock_prompt.assert_not_called()

    def test_get_building_single_match(self):
        """Test get_building with single match."""
        submit = Submit(receipt_file=Path('test.pdf'))

        # Mock contract
        mock_contract = MagicMock()
        mock_contract.load_buildings.return_value = [Building(id='b1', name='Hospital A', address='123 Main St')]
        submit.contract = mock_contract

        result, nif = submit.get_building('123456789')

        self.assertEqual(result.id, 'b1')
        self.assertEqual(result.name, 'Hospital A')
        self.assertEqual(nif, '123456789')

    def test_get_building_multiple_matches_interactive(self):
        """Test get_building with multiple matches - interactive selection."""
        submit = Submit(receipt_file=Path('test.pdf'), interactive=True)

        # Mock contract
        mock_contract = MagicMock()
        mock_contract.load_buildings.return_value = [
            Building(id='b1', name='Hospital A', address='123 Main St'),
            Building(id='b2', name='Hospital B', address='456 Oak St'),
        ]
        submit.contract = mock_contract

        with patch('click.prompt', return_value=1):
            result, nif = submit.get_building('123456789')

        self.assertEqual(result.id, 'b1')
        self.assertEqual(result.name, 'Hospital A')

    def test_get_building_multiple_matches_non_interactive(self):
        """Test get_building with multiple matches fails without prompting by default."""
        submit = Submit(receipt_file=Path('test.pdf'))

        mock_contract = MagicMock()
        mock_contract.load_buildings.return_value = [
            Building(id='b1', name='Hospital A', address='123 Main St'),
            Building(id='b2', name='Hospital B', address='456 Oak St'),
        ]
        submit.contract = mock_contract

        with patch('click.prompt') as mock_prompt:
            with self.assertRaisesRegex(click.ClickException, 'Multiple buildings found for 123456789'):
                submit.get_building('123456789')

        mock_prompt.assert_not_called()

    def test_get_building_multiple_matches_building(self):
        """Test get_building with multiple matches and preselected building name."""
        submit = Submit(receipt_file=Path('test.pdf'), building='Hospital B')

        mock_contract = MagicMock()
        mock_contract.load_buildings.return_value = [
            Building(id='b1', name='Hospital A', address='123 Main St'),
            Building(id='b2', name='Hospital B', address='456 Oak St'),
        ]
        submit.contract = mock_contract

        with patch('click.prompt') as mock_prompt:
            result, nif = submit.get_building('123456789')

        mock_prompt.assert_not_called()
        self.assertEqual(result.id, 'b2')
        self.assertEqual(result.name, 'Hospital B')
        self.assertEqual(nif, '123456789')

    def test_get_building_building_not_found(self):
        """Test get_building rejects an unknown preselected building name."""
        submit = Submit(receipt_file=Path('test.pdf'), building='Hospital C')

        mock_contract = MagicMock()
        mock_contract.load_buildings.return_value = [
            Building(id='b1', name='Hospital A', address='123 Main St'),
            Building(id='b2', name='Hospital B', address='456 Oak St'),
        ]
        submit.contract = mock_contract

        with self.assertRaisesRegex(click.ClickException, "No building found named 'Hospital C' for 123456789"):
            submit.get_building('123456789')

    def test_get_building_building_ambiguous(self):
        """Test get_building rejects an ambiguous preselected building name."""
        submit = Submit(receipt_file=Path('test.pdf'), building='Hospital A')

        mock_contract = MagicMock()
        mock_contract.load_buildings.return_value = [
            Building(id='b1', name='Hospital A', address='123 Main St'),
            Building(id='b2', name='Hospital A', address='456 Oak St'),
        ]
        submit.contract = mock_contract

        with self.assertRaisesRegex(click.ClickException, "Multiple buildings named 'Hospital A' found for 123456789"):
            submit.get_building('123456789')

    def test_get_building_invalid_nif(self):
        """Test get_building with invalid NIF."""
        submit = Submit(receipt_file=Path('test.pdf'), interactive=True)
        mock_contract = MagicMock()
        mock_contract.load_buildings.return_value = [Building(id='x', name='x', address='x')]
        submit.contract = mock_contract

        with patch('click.prompt', return_value='123456789') as mock_prompt:
            result, nif = submit.get_building('invalid')

        mock_prompt.assert_called_once()
        self.assertEqual(result.id, 'x')
        self.assertEqual(nif, '123456789')

    def test_get_building_invalid_nif_non_interactive(self):
        """Test get_building rejects an invalid NIF without prompting by default."""
        submit = Submit(receipt_file=Path('test.pdf'))
        mock_contract = MagicMock()
        submit.contract = mock_contract

        with patch('click.prompt') as mock_prompt:
            with self.assertRaisesRegex(click.ClickException, 'invalid is not a valid NIF'):
                submit.get_building('invalid')

        mock_prompt.assert_not_called()
        mock_contract.load_buildings.assert_not_called()

    def test_get_building_no_buildings(self):
        """Test get_building when no buildings found for NIF."""
        submit = Submit(receipt_file=Path('test.pdf'), interactive=True)

        # Mock contract
        mock_contract = MagicMock()
        mock_contract.load_buildings.side_effect = [[], [Building(id='x', name='x', address='x')]]
        submit.contract = mock_contract

        with patch('click.prompt', return_value='505956985') as mock_prompt:
            result, nif = submit.get_building('123456789')

        # Should prompt for new NIF
        self.assertEqual(mock_prompt.call_count, 1)
        self.assertEqual(result.id, 'x')
        self.assertEqual(nif, '505956985')

    def test_get_building_no_buildings_non_interactive(self):
        """Test get_building rejects a NIF with no buildings without prompting by default."""
        submit = Submit(receipt_file=Path('test.pdf'))

        mock_contract = MagicMock()
        mock_contract.load_buildings.return_value = []
        submit.contract = mock_contract

        with patch('click.prompt') as mock_prompt:
            with self.assertRaisesRegex(click.ClickException, '123456789 has no buildings'):
                submit.get_building('123456789')

        mock_prompt.assert_not_called()
