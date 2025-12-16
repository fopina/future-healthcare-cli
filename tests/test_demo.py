import unittest

from futurehealth.commands import login


class Test(unittest.TestCase):
    def test_login(self):
        cmd = login.Login(username='x')
        self.assertEqual(cmd.username, 'x')
