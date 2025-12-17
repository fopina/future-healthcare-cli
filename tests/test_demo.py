import unittest

from futurehealth.commands import login


class Test(unittest.TestCase):
    def test_login(self):
        cmd = login.Login(username='x')
        self.assertEqual(cmd.username, 'x')

    def test_model_field_assignment(self):
        from futurehealth.utils.models import ReceiptData

        b = ReceiptData(business_nif='', date='', invoice_number='', total_amount='10.0')
        self.assertEqual(b.total_amount, 10)
        b.total_amount = '12.0'
        self.assertEqual(b.total_amount, 12)
