from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from futurehealth.client.models import Building, Person, Service
from futurehealth.commands.submit import Submit
from futurehealth.utils.models import ReceiptData


class TestSubmitCommand:
    """Test cases for the Submit command."""

    def test_submit_initialization(self):
        """Test Submit command initialization with options."""
        submit = Submit(
            receipt_file=Path('test.pdf'),
            person='John',
            service='Medical',
            openai_api_key='test_key',
            openai_api_url='https://test.api',
            openai_model_vision='test-vision',
            openai_model_text='test-text',
            force_vision=False,
            vision_dpi=200,
            debug=True,
        )

        assert submit.receipt_file == Path('test.pdf')
        assert submit.person == 'John'
        assert submit.service == 'Medical'
        assert submit.openai_api_key == 'test_key'
        assert submit.openai_api_url == 'https://test.api'
        assert submit.openai_model_vision == 'test-vision'
        assert submit.openai_model_text == 'test-text'
        assert submit.force_vision is False
        assert submit.vision_dpi == 200
        assert submit.debug is True

    @patch('futurehealth.commands.submit.Submit.setup_logging')
    @patch('futurehealth.commands.submit.Submit.parse_receipt')
    @patch('futurehealth.commands.submit.Submit.get_building')
    @patch('futurehealth.commands.submit.Submit.get_service')
    @patch('futurehealth.commands.submit.Submit.get_person')
    @patch('futurehealth.commands.submit.Submit.review_data')
    @patch('futurehealth.client.Client')
    @patch('futurehealth.client.ContractClient')
    def test_submit_full_flow(
        self,
        mock_contract_client,
        mock_client_class,
        mock_review,
        mock_get_person,
        mock_get_service,
        mock_get_building,
        mock_parse_receipt,
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

        # Mock data and selections
        mock_data = ReceiptData(
            business_nif='123456789',
            personal_nif='987654321',
            invoice_number='INV001',
            total_amount=100.50,
            date='2023-01-01',
        )
        mock_parse_receipt.return_value = mock_data

        mock_building = Building(id='building_123', name='Hospital A', address='123 Main St')
        mock_get_building.return_value = (mock_building, '123456789')

        mock_service = Service(id=1, name='Medical Service', mantory_invoice_file=True, mantory_additional_file=False)
        mock_get_service.return_value = mock_service

        mock_person = Person(card_number='123456789', name='John Doe', email='john@example.com')
        mock_get_person.return_value = mock_person

        # Create submit command
        submit = Submit(receipt_file=Path('test.pdf'))
        submit.contract = mock_contract
        submit.file_logger = MagicMock()
        submit.console_logger = MagicMock()

        # Execute
        submit()

        # Verify calls
        mock_setup_logging.assert_called_once()
        mock_parse_receipt.assert_called_once()
        mock_review.assert_called_once_with(mock_data)
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
    @patch('futurehealth.commands.submit.Submit.parse_receipt')
    @patch('futurehealth.commands.submit.Submit.review_data')
    @patch('futurehealth.commands.submit.client.Client')
    def test_submit_feature_not_available(self, mock_client_class, mock_review, mock_parse_receipt, mock_setup_logging):
        """Test submit when REFUNDS_SUBMISSION feature is not available."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_contract = MagicMock()
        mock_contract.validate_feature.return_value = False

        mock_parse_receipt.return_value = ReceiptData(business_nif='1', invoice_number='1', total_amount=1, date='1')

        submit = Submit(receipt_file=Path('test.pdf'))
        submit.contract = mock_contract
        submit.file_logger = MagicMock()
        submit.console_logger = MagicMock()

        with pytest.raises(AssertionError):
            submit()

    @patch('futurehealth.commands.submit.utils.read_pdf')
    @patch('futurehealth.commands.submit.OpenAI')
    def test_parse_receipt_text_mode(self, mock_openai_class, mock_read_pdf):
        """Test parse_receipt in text mode."""
        # Mock PDF reading - return text content
        mock_read_pdf.return_value = [{'type': 'text', 'text': 'Sample receipt text'}]

        # Mock OpenAI client
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[
            0
        ].message.content = '{"business_nif": "123456789", "personal_nif": "987654321", "invoice_number": "INV001", "total_amount": "100.50", "date": "01/01/2023"}'
        mock_completion.usage = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion

        submit = Submit(receipt_file=Path('test.pdf'))
        submit.file_logger = MagicMock()
        submit.console_logger = MagicMock()
        submit.openai_api_key = 'test_key'
        submit.openai_api_url = 'https://test.api'
        submit.openai_model_text = 'test-model'

        result = submit.parse_receipt()

        assert isinstance(result, ReceiptData)
        assert result.business_nif == '123456789'
        assert result.personal_nif == '987654321'
        assert result.invoice_number == 'INV001'
        assert result.total_amount == 100.50
        assert result.date == '2023-01-01'  # Should be reformatted

        # Verify OpenAI call
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]['model'] == 'test-model'
        assert len(call_args[1]['messages']) == 2  # system + user

    @patch('futurehealth.commands.submit.utils.read_pdf')
    @patch('futurehealth.commands.submit.OpenAI')
    def test_parse_receipt_vision_mode(self, mock_openai_class, mock_read_pdf):
        """Test parse_receipt in vision mode."""
        # Mock PDF reading - return image content
        mock_read_pdf.return_value = [{'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,test'}}]

        # Mock OpenAI client
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[
            0
        ].message.content = '{"business_nif": "123456789", "personal_nif": "987654321", "invoice_number": "INV001", "total_amount": "100.50", "date": "01/01/2023"}'
        mock_completion.usage = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion

        submit = Submit(receipt_file=Path('test.pdf'))
        submit.file_logger = MagicMock()
        submit.console_logger = MagicMock()
        submit.openai_api_key = 'test_key'
        submit.openai_api_url = 'https://test.api'
        submit.openai_model_vision = 'vision-model'
        submit.force_vision = False

        result = submit.parse_receipt()

        assert isinstance(result, ReceiptData)
        assert result.business_nif == '123456789'

        # Verify vision model was used
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]['model'] == 'vision-model'

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

        assert result.id == 1
        assert result.name == 'Medical Service'

    def test_get_service_multiple_matches_interactive(self):
        """Test get_service with multiple matches - interactive selection."""
        submit = Submit(receipt_file=Path('test.pdf'), service=None)

        # Mock refunds_request_setup
        mock_setup = MagicMock()
        mock_setup.services = [
            Service(Id=1, Name='Medical Service A', IsMandatoryInvoiceFile=True, IsMandatoryAditionalFile=False),
            Service(Id=2, Name='Medical Service B', IsMandatoryInvoiceFile=True, IsMandatoryAditionalFile=False),
        ]
        submit.refunds_request_setup = mock_setup

        with patch('click.prompt', return_value=1):
            result = submit.get_service()

        assert result.id == 1
        assert result.name == 'Medical Service A'

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

        with pytest.raises(Exception):  # ClickException
            submit.get_service()

    def test_get_person_single_match(self):
        """Test get_person with single match."""
        submit = Submit(receipt_file=Path('test.pdf'), person=None)

        # Mock refunds_request_setup
        mock_setup = MagicMock()
        mock_setup.insured_persons = [Person(CardNumber='123456789', Name='John Doe', Email='john@example.com')]
        submit.refunds_request_setup = mock_setup

        result = submit.get_person()

        assert result.card_number == '123456789'
        assert result.name == 'John Doe'

    def test_get_person_multiple_matches_interactive(self):
        """Test get_person with multiple matches - interactive selection."""
        submit = Submit(receipt_file=Path('test.pdf'), person=None)

        # Mock refunds_request_setup
        mock_setup = MagicMock()
        mock_setup.insured_persons = [
            Person(CardNumber='123456789', Name='John Doe', Email='john@example.com'),
            Person(CardNumber='987654321', Name='Jane Smith', Email='jane@example.com'),
        ]
        submit.refunds_request_setup = mock_setup

        with patch('click.prompt', return_value=2):
            result = submit.get_person()

        assert result.card_number == '987654321'
        assert result.name == 'Jane Smith'

    def test_get_building_single_match(self):
        """Test get_building with single match."""
        submit = Submit(receipt_file=Path('test.pdf'))

        # Mock contract
        mock_contract = MagicMock()
        mock_contract.load_buildings.return_value = [Building(id='b1', name='Hospital A', address='123 Main St')]
        submit.contract = mock_contract

        result, nif = submit.get_building('123456789')

        assert result.id == 'b1'
        assert result.name == 'Hospital A'
        assert nif == '123456789'

    def test_get_building_multiple_matches_interactive(self):
        """Test get_building with multiple matches - interactive selection."""
        submit = Submit(receipt_file=Path('test.pdf'))

        # Mock contract
        mock_contract = MagicMock()
        mock_contract.load_buildings.return_value = [
            Building(id='b1', name='Hospital A', address='123 Main St'),
            Building(id='b2', name='Hospital B', address='456 Oak St'),
        ]
        submit.contract = mock_contract

        with patch('click.prompt', return_value=1):
            result, nif = submit.get_building('123456789')

        assert result.id == 'b1'
        assert result.name == 'Hospital A'

    def test_get_building_invalid_nif(self):
        """Test get_building with invalid NIF."""
        submit = Submit(receipt_file=Path('test.pdf'))
        mock_contract = MagicMock()
        mock_contract.load_buildings.return_value = [Building(id='x', name='x', address='x')]
        submit.contract = mock_contract

        with patch('click.prompt', return_value='123456789') as mock_prompt:
            result, nif = submit.get_building('invalid')

        mock_prompt.assert_called_once()
        assert result.id == 'x'
        assert nif == '123456789'

    def test_get_building_no_buildings(self):
        """Test get_building when no buildings found for NIF."""
        submit = Submit(receipt_file=Path('test.pdf'))

        # Mock contract
        mock_contract = MagicMock()
        mock_contract.load_buildings.side_effect = [[], [Building(id='x', name='x', address='x')]]
        submit.contract = mock_contract

        with patch('click.prompt', return_value='505956985') as mock_prompt:
            result, nif = submit.get_building('123456789')

        # Should prompt for new NIF
        assert mock_prompt.call_count == 1
        assert result.id == 'x'
        assert nif == '505956985'

    @patch('futurehealth.utils.models.ReceiptData.model_copy')
    def test_review_data_update_field(self, mock_model_copy):
        """Test review_data field update functionality."""
        submit = Submit(receipt_file=Path('test.pdf'))

        data = ReceiptData(
            business_nif='123456789',
            personal_nif='987654321',
            invoice_number='INV001',
            total_amount=100.50,
            date='2023-01-01',
        )

        with patch('click.prompt') as mock_prompt:
            # First call returns 2 (invoice_number field), second call returns 0 (done)
            mock_prompt.side_effect = [2, 'INV002', 0]

            submit.review_data(data)

        assert data.invoice_number == 'INV002'

    def test_review_data_all_good(self):
        """Test review_data when user selects 'All good'."""
        submit = Submit(receipt_file=Path('test.pdf'))

        data = ReceiptData(
            business_nif='123456789',
            personal_nif='987654321',
            invoice_number='INV001',
            total_amount=100.50,
            date='2023-01-01',
        )

        with patch('click.prompt', return_value=0):  # All good
            submit.review_data(data)
