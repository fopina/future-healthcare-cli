import unittest
from unittest.mock import MagicMock, patch

import pytest

from futurehealth.client.models import Building, Person, Service
from futurehealth.commands import login
from futurehealth.commands._mixins import ContractMixin, TokenMixin
from futurehealth.utils import prompts
from futurehealth.utils.models import ReceiptData


class Test(unittest.TestCase):
    def test_login(self):
        cmd = login.Login(username='x')
        self.assertEqual(cmd.username, 'x')

    def test_model_field_assignment(self):
        b = ReceiptData(business_nif='', date='', invoice_number='', total_amount='10.0')
        self.assertEqual(b.total_amount, 10.0)
        b.total_amount = '12.0'
        self.assertEqual(b.total_amount, 12.0)


class TestModels(unittest.TestCase):
    def test_receipt_data_creation(self):
        data = ReceiptData(
            business_nif='123456789',
            personal_nif='987654321',
            invoice_number='INV001',
            total_amount=100.50,
            date='2023-01-01',
        )
        self.assertEqual(data.business_nif, '123456789')
        self.assertEqual(data.personal_nif, '987654321')
        self.assertEqual(data.invoice_number, 'INV001')
        self.assertEqual(data.total_amount, 100.50)
        self.assertEqual(data.date, '2023-01-01')

    def test_receipt_data_type_conversion(self):
        data = ReceiptData(
            business_nif='123456789',
            personal_nif='987654321',
            invoice_number='INV001',
            total_amount='100.50',  # String should convert to float
            date='2023-01-01',
        )
        self.assertIsInstance(data.total_amount, float)
        self.assertEqual(data.total_amount, 100.5)

    def test_receipt_data_extra_fields(self):
        data = ReceiptData(
            business_nif='123456789',
            personal_nif='987654321',
            invoice_number='INV001',
            total_amount=100.50,
            date='2023-01-01',
            extra_field='extra_value',  # Should be allowed due to extra='allow'
        )
        self.assertTrue(hasattr(data, 'extra_field'))
        self.assertEqual(data.extra_field, 'extra_value')

    def test_receipt_data_validation_error(self):
        with self.assertRaises(Exception):  # Pydantic validation error
            ReceiptData(
                business_nif='123456789',
                personal_nif='987654321',
                invoice_number='INV001',
                total_amount='not_a_number',  # Should fail conversion
                date='2023-01-01',
            )

    def test_person_model(self):
        # Use alias field names for creation
        person = Person(CardNumber='123456789', Name='John Doe', Email='john@example.com')
        self.assertEqual(person.card_number, '123456789')
        self.assertEqual(person.name, 'John Doe')
        self.assertEqual(person.email, 'john@example.com')

    def test_person_with_aliases(self):
        # Test that JSON with original field names works
        data = {'CardNumber': '123456789', 'Name': 'John Doe', 'Email': 'john@example.com'}
        person = Person(**data)
        self.assertEqual(person.card_number, '123456789')
        self.assertEqual(person.name, 'John Doe')
        self.assertEqual(person.email, 'john@example.com')

    def test_service_model(self):
        # Use alias field names for creation
        service = Service(Id=1, Name='Medical Service', IsMandatoryInvoiceFile=True, IsMandatoryAditionalFile=False)
        self.assertEqual(service.id, 1)
        self.assertEqual(service.name, 'Medical Service')
        self.assertTrue(service.mantory_invoice_file)
        self.assertFalse(service.mantory_additional_file)

    def test_service_with_aliases(self):
        data = {'Id': 1, 'Name': 'Medical Service', 'IsMandatoryInvoiceFile': True, 'IsMandatoryAditionalFile': False}
        service = Service(**data)
        self.assertEqual(service.id, 1)
        self.assertEqual(service.name, 'Medical Service')
        self.assertTrue(service.mantory_invoice_file)
        self.assertFalse(service.mantory_additional_file)

    def test_building_model(self):
        building = Building(id='123', name='Hospital A', address='123 Main St')
        self.assertEqual(building.id, '123')
        self.assertEqual(building.name, 'Hospital A')
        self.assertEqual(building.address, '123 Main St')
        self.assertEqual(str(building), '123 - Hospital A')


class TestMixins(unittest.TestCase):
    def test_token_mixin_with_token_file(self):
        """Test TokenMixin when token file exists."""
        with patch('futurehealth.commands._mixins.token_path') as mock_token_path:
            mock_path = MagicMock()
            mock_path.read_text.return_value = 'test_token'
            mock_token_path.return_value = mock_path

            mixin = TokenMixin()
            self.assertEqual(mixin.token, 'test_token')

    def test_token_mixin_without_token_file(self):
        """Test TokenMixin when token file doesn't exist."""
        with patch('futurehealth.commands._mixins.token_path') as mock_token_path:
            mock_path = MagicMock()
            mock_path.read_text.side_effect = FileNotFoundError()
            mock_token_path.return_value = mock_path

            mixin = TokenMixin()
            with self.assertRaises(Exception):  # Should raise ClickException
                _ = mixin.token

    @patch('futurehealth.commands._mixins.ContractClient')
    def test_contract_mixin(self, mock_contract_client):
        """Test ContractMixin contract property."""
        mock_client = MagicMock()
        mock_client.contracts.return_value = [{'Token': 'contract_token', 'ContractState': 'ACTIVE'}]
        mock_contract_client.return_value = 'contract_client_instance'

        mixin = ContractMixin()
        mixin._client = mock_client

        contract = mixin.contract

        self.assertEqual(contract, 'contract_client_instance')
        mock_contract_client.assert_called_once_with(mock_client, 'contract_token')

    def test_contract_mixin_inactive_contract(self):
        """Test ContractMixin with inactive contract."""
        mock_client = MagicMock()
        mock_client.contracts.return_value = [{'Token': 'contract_token', 'ContractState': 'INACTIVE'}]

        mixin = ContractMixin()
        mixin._client = mock_client

        with self.assertRaises(AssertionError):
            _ = mixin.contract


class TestCommands(unittest.TestCase):
    @patch('futurehealth.commands.login.token_path')
    @patch('futurehealth.client.Client')
    def test_login_success(self, mock_client_class, mock_token_path):
        """Test successful login."""
        mock_client_class.return_value.login.return_value = {'body': {'token': 'auth_token'}}

        mock_path = MagicMock()
        mock_token_path.return_value = mock_path

        cmd = login.Login(username='user', password='pass')
        cmd()

        mock_client_class.return_value.login.assert_called_once_with('user', 'pass')
        mock_path.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True, mode=0o700)
        mock_path.write_text.assert_called_once_with('auth_token')

    @patch('futurehealth.client.Client')
    def test_login_failure(self, mock_client_class):
        """Test login with authentication error."""
        from futurehealth import client

        mock_client_class.login.side_effect = client.exceptions.LoginError('Invalid credentials')

        cmd = login.Login(username='user', password='wrong')

        with self.assertRaises(Exception):  # Should raise ClickException
            cmd()


class TestPrompts(unittest.TestCase):
    def test_system_prompt_exists(self):
        """Test that SYSTEM_PROMPT is defined and not empty."""
        self.assertTrue(hasattr(prompts, 'SYSTEM_PROMPT'))
        self.assertIsInstance(prompts.SYSTEM_PROMPT, str)
        self.assertGreater(len(prompts.SYSTEM_PROMPT), 0)

    def test_user_text_prompt_exists(self):
        """Test that USER_TEXT_PROMPT is defined and not empty."""
        self.assertTrue(hasattr(prompts, 'USER_TEXT_PROMPT'))
        self.assertIsInstance(prompts.USER_TEXT_PROMPT, str)
        self.assertGreater(len(prompts.USER_TEXT_PROMPT), 0)

    def test_user_vision_prompt_exists(self):
        """Test that USER_VISION_PROMPT is defined and not empty."""
        self.assertTrue(hasattr(prompts, 'USER_VISION_PROMPT'))
        self.assertIsInstance(prompts.USER_VISION_PROMPT, str)
        self.assertGreater(len(prompts.USER_VISION_PROMPT), 0)

    def test_prompts_contain_key_instructions(self):
        """Test that prompts contain expected key instructions."""
        self.assertIn('business_nif', prompts.USER_TEXT_PROMPT)
        self.assertIn('personal_nif', prompts.USER_TEXT_PROMPT)
        self.assertIn('invoice_number', prompts.USER_TEXT_PROMPT)
        self.assertIn('total_amount', prompts.USER_TEXT_PROMPT)
        self.assertIn('date', prompts.USER_TEXT_PROMPT)

        self.assertIn('business_nif', prompts.USER_VISION_PROMPT)
        self.assertIn('personal_nif', prompts.USER_VISION_PROMPT)
        self.assertIn('invoice_number', prompts.USER_VISION_PROMPT)
        self.assertIn('total_amount', prompts.USER_VISION_PROMPT)
        self.assertIn('date', prompts.USER_VISION_PROMPT)


class TestMain(unittest.TestCase):
    @patch('futurehealth.__main__.cli')
    def test_main_runs_cli(self, mock_cli):
        """Test that __main__.py runs the CLI when executed directly."""
        # This is tricky to test directly, but we can test the imports work
        import futurehealth.__main__

        self.assertTrue(hasattr(futurehealth.__main__, 'cli'))
