import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from futurehealth import utils
from futurehealth.client.models import Building, Person, Service
from futurehealth.commands import login
from futurehealth.commands._mixins import ContractMixin, TokenMixin
from futurehealth.commands.beneficiaries import Beneficiaries
from futurehealth.commands.cli import CLI
from futurehealth.commands.config import Config
from futurehealth.commands.nifs import Nifs
from futurehealth.commands.services import Services
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
            invoice_number='INV001',
            total_amount=100.50,
            date='2023-01-01',
        )
        self.assertEqual(data.business_nif, '123456789')
        self.assertEqual(data.invoice_number, 'INV001')
        self.assertEqual(data.total_amount, 100.50)
        self.assertEqual(data.date, '2023-01-01')

    def test_receipt_data_type_conversion(self):
        data = ReceiptData(
            business_nif='123456789',
            invoice_number='INV001',
            total_amount='100.50',  # String should convert to float
            date='2023-01-01',
        )
        self.assertIsInstance(data.total_amount, float)
        self.assertEqual(data.total_amount, 100.5)

    def test_receipt_data_extra_fields(self):
        data = ReceiptData(
            business_nif='123456789',
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

    @patch('futurehealth.commands._mixins.Client')
    def test_token_mixin_client_uses_default_language(self, mock_client_class):
        mixin = TokenMixin()
        mixin.__dict__['token'] = 'test_token'

        self.assertIs(mixin.client, mock_client_class.return_value)
        mock_client_class.assert_called_once_with(token='test_token', verify=True)

    @patch('futurehealth.commands._mixins.ContractClient')
    def test_contract_mixin(self, mock_contract_client):
        """Test ContractMixin contract property."""
        mock_client = MagicMock()
        mock_client.contracts.return_value = [{'Token': 'contract_token', 'ContractState': 'ACTIVE'}]
        mock_contract_client.return_value = 'contract_client_instance'

        mixin = ContractMixin()
        mixin.client = mock_client

        contract = mixin.contract

        self.assertEqual(contract, 'contract_client_instance')
        mock_contract_client.assert_called_once_with(mock_client, 'contract_token')

    def test_contract_mixin_inactive_contract(self):
        """Test ContractMixin with inactive contract."""
        mock_client = MagicMock()
        mock_client.contracts.return_value = [{'Token': 'contract_token', 'ContractState': 'INACTIVE'}]

        mixin = ContractMixin()
        mixin.client = mock_client

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

        mock_client_class.assert_called_once_with(verify=True)
        mock_client_class.return_value.login.assert_called_once_with('user', 'pass')
        mock_path.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True, mode=0o700)
        mock_path.write_text.assert_called_once_with('auth_token')

    @patch('futurehealth.client.Client')
    def test_login_failure(self, mock_client_class):
        """Test login with authentication error."""
        from futurehealth import client

        mock_client_class.return_value.login.side_effect = client.exceptions.LoginError('Invalid credentials')

        cmd = login.Login(username='user', password='wrong')

        with self.assertRaises(Exception):  # Should raise ClickException
            cmd()

    @patch('futurehealth.client.Client')
    def test_group_token_path_option_controls_login_storage(self, mock_client_class):
        """Test login writes to the group-level token path."""
        mock_client_class.return_value.login.return_value = {'body': {'token': 'auth_token'}}

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / 'config.toml'
            token_file = tmp_path / 'tokens' / 'token.txt'

            result = CliRunner().invoke(
                CLI.click,
                [
                    '--config',
                    str(config_path),
                    '--token-path',
                    str(token_file),
                    '--locale',
                    'en-US',
                    'login',
                    '-u',
                    'user',
                    '-p',
                    'pass',
                ],
            )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertEqual(token_file.read_text(), 'auth_token')
            mock_client_class.assert_called_once_with(verify=True)

    @patch('futurehealth.client.Client')
    def test_group_locale_option_does_not_control_login_client_language(self, mock_client_class):
        mock_client_class.return_value.login.return_value = {'body': {'token': 'auth_token'}}

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            token_file = tmp_path / 'token.txt'

            result = CliRunner().invoke(
                CLI.click,
                [
                    '--token-path',
                    str(token_file),
                    '--locale',
                    'pt-PT',
                    'login',
                    '-u',
                    'user',
                    '-p',
                    'pass',
                ],
            )

            self.assertEqual(result.exit_code, 0, result.output)
            mock_client_class.assert_called_once_with(verify=True)

    def test_group_locale_option_rejects_unsupported_locale(self):
        result = CliRunner().invoke(CLI.click, ['--locale', 'fr-FR', 'config'])

        self.assertNotEqual(result.exit_code, 0, result.output)
        self.assertIn('Locale must be one of: pt-PT, en-US', result.output)

    def test_group_locale_help_shows_detected_default(self):
        result = CliRunner().invoke(CLI.click, ['--help'])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn(f'[default: {utils.locale()}]', result.output)
        self.assertNotIn('system locale, falling back to en-US', result.output)

    @patch('futurehealth.client.Client')
    def test_login_token_path_defaults_next_to_config(self, mock_client_class):
        """Test login stores the token next to the selected config file by default."""
        mock_client_class.return_value.login.return_value = {'body': {'token': 'auth_token'}}

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / 'nested' / 'config.toml'
            token_file = config_path.parent / 'token.txt'

            result = CliRunner().invoke(
                CLI.click,
                [
                    '--config',
                    str(config_path),
                    'login',
                    '-u',
                    'user',
                    '-p',
                    'pass',
                ],
            )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertEqual(token_file.read_text(), 'auth_token')


class TestMain(unittest.TestCase):
    @patch('futurehealth.commands.cli.CLI.click')
    def test_main_runs_cli(self, mock_cli):
        """Test that __main__.py dispatches to the CLI entrypoint."""
        import futurehealth.__main__

        futurehealth.__main__.main()

        mock_cli.assert_called_once()

    def test_cli_registers_config_command(self):
        """Test the app exposes the ClassyClick config command."""
        self.assertIs(CLI.click.commands['config'], Config.click)

    def test_cli_registers_services_command(self):
        """Test the app exposes the services command."""
        self.assertIs(CLI.click.commands['services'], Services.click)

    def test_cli_registers_beneficiaries_command(self):
        """Test the app exposes the beneficiaries command."""
        self.assertIs(CLI.click.commands['beneficiaries'], Beneficiaries.click)

    def test_cli_registers_nifs_command(self):
        """Test the app exposes the NIF lookup command."""
        self.assertIs(CLI.click.commands['nifs'], Nifs.click)
