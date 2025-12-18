import unittest

import pytest

from futurehealth.client.models import Building, Person, Service
from futurehealth.commands import login
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


class TestModels:
    def test_receipt_data_creation(self):
        data = ReceiptData(
            business_nif='123456789',
            personal_nif='987654321',
            invoice_number='INV001',
            total_amount=100.50,
            date='2023-01-01',
        )
        assert data.business_nif == '123456789'
        assert data.personal_nif == '987654321'
        assert data.invoice_number == 'INV001'
        assert data.total_amount == 100.50
        assert data.date == '2023-01-01'

    def test_receipt_data_type_conversion(self):
        data = ReceiptData(
            business_nif='123456789',
            personal_nif='987654321',
            invoice_number='INV001',
            total_amount='100.50',  # String should convert to float
            date='2023-01-01',
        )
        assert isinstance(data.total_amount, float)
        assert data.total_amount == 100.5

    def test_receipt_data_extra_fields(self):
        data = ReceiptData(
            business_nif='123456789',
            personal_nif='987654321',
            invoice_number='INV001',
            total_amount=100.50,
            date='2023-01-01',
            extra_field='extra_value',  # Should be allowed due to extra='allow'
        )
        assert hasattr(data, 'extra_field')
        assert data.extra_field == 'extra_value'

    def test_receipt_data_validation_error(self):
        with pytest.raises(Exception):  # Pydantic validation error
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
        assert person.card_number == '123456789'
        assert person.name == 'John Doe'
        assert person.email == 'john@example.com'

    def test_person_with_aliases(self):
        # Test that JSON with original field names works
        data = {'CardNumber': '123456789', 'Name': 'John Doe', 'Email': 'john@example.com'}
        person = Person(**data)
        assert person.card_number == '123456789'
        assert person.name == 'John Doe'
        assert person.email == 'john@example.com'

    def test_service_model(self):
        # Use alias field names for creation
        service = Service(Id=1, Name='Medical Service', IsMandatoryInvoiceFile=True, IsMandatoryAditionalFile=False)
        assert service.id == 1
        assert service.name == 'Medical Service'
        assert service.mantory_invoice_file is True
        assert service.mantory_additional_file is False

    def test_service_with_aliases(self):
        data = {'Id': 1, 'Name': 'Medical Service', 'IsMandatoryInvoiceFile': True, 'IsMandatoryAditionalFile': False}
        service = Service(**data)
        assert service.id == 1
        assert service.name == 'Medical Service'
        assert service.mantory_invoice_file is True
        assert service.mantory_additional_file is False

    def test_building_model(self):
        building = Building(id='123', name='Hospital A', address='123 Main St')
        assert building.id == '123'
        assert building.name == 'Hospital A'
        assert building.address == '123 Main St'
        assert str(building) == '123 - Hospital A'
