import unittest

import futurehealth.demo

import futurehealth


class Test(unittest.TestCase):
    # TODO: update with your own unit tests and assertions
    def test_echo(self):
        self.assertEqual(futurehealth.demo.echo('hey'), 'HEY right back at ya!')
