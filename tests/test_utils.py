import unittest
from pathlib import Path
from unittest.mock import patch

from futurehealth.commands.cli import CLI
from futurehealth.utils import errors_path, logs_path, token_path, validate_nif
from futurehealth.utils import locale as fh_locale


class TestPaths(unittest.TestCase):
    def test_default_paths_are_next_to_config(self):
        self.assertEqual(token_path(), CLI.CONFIG_DEFAULT_PATH.parent / 'token.txt')
        self.assertEqual(logs_path(), CLI.CONFIG_DEFAULT_PATH.parent / 'logs')
        self.assertEqual(errors_path(), CLI.CONFIG_DEFAULT_PATH.parent / 'errors.json')

    def test_paths_are_next_to_custom_config(self):
        config = Path('/tmp/future-healthcare/config.toml')

        self.assertEqual(token_path(config), Path('/tmp/future-healthcare/token.txt'))
        self.assertEqual(logs_path(config), Path('/tmp/future-healthcare/logs'))
        self.assertEqual(errors_path(config), Path('/tmp/future-healthcare/errors.json'))

    def test_explicit_paths_override_config_defaults(self):
        config = Path('/tmp/future-healthcare/config.toml')

        self.assertEqual(
            token_path(config, override='/tmp/other/token.txt'),
            Path('/tmp/other/token.txt'),
        )
        self.assertEqual(
            logs_path(config, override='/tmp/other/logs'),
            Path('/tmp/other/logs'),
        )
        self.assertEqual(
            errors_path(config, override='/tmp/other/errors.json'),
            Path('/tmp/other/errors.json'),
        )


class TestLocale(unittest.TestCase):
    def test_locale_uses_supported_system_locale(self):
        with patch('futurehealth.utils.system_locale.getlocale', return_value=('pt_PT', 'UTF-8')):
            self.assertEqual(fh_locale(), 'pt-PT')

    def test_locale_falls_back_to_english_for_unsupported_system_locale(self):
        with patch('futurehealth.utils.system_locale.getlocale', return_value=('fr_FR', 'UTF-8')):
            self.assertEqual(fh_locale(), 'en-US')

    def test_locale_accepts_supported_override(self):
        self.assertEqual(fh_locale(override='en-US'), 'en-US')
        self.assertEqual(fh_locale(override='pt_PT'), 'pt-PT')

    def test_locale_rejects_unsupported_override(self):
        with self.assertRaises(ValueError):
            fh_locale(override='fr-FR')


class TestValidateNIF(unittest.TestCase):
    """Test cases for Portuguese NIF validation using mod11 algorithm."""

    def test_valid_nifs(self):
        """Test that valid NIFs pass validation."""
        valid_nifs = [
            '123456789',  # Valid personal NIF
            '505956985',  # Valid business NIF (starts with 5)
            ' 123 456 789 ',  # Valid with spaces (should be cleaned)
        ]

        for nif in valid_nifs:
            self.assertTrue(validate_nif(nif), f'NIF {nif} should be valid')

    def test_invalid_nifs(self):
        """Test that invalid NIFs fail validation."""
        invalid_nifs = [
            '123456780',  # Wrong check digit
            '999999999',  # Invalid check digit
            '12345678',  # Too short (8 digits)
            '1234567890',  # Too long (10 digits)
            '12345678a',  # Contains letter
            'abcdefgh',  # All letters
            '',  # Empty string
            '123.456.78',  # With dots, becomes 12345678 (too short)
        ]

        for nif in invalid_nifs:
            self.assertFalse(validate_nif(nif), f'NIF {nif} should be invalid')

    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Test with various formatting
        self.assertTrue(validate_nif('123-456-789'))  # With dashes
        self.assertTrue(validate_nif('123 456 789'))  # With spaces
        self.assertTrue(validate_nif('123456789'))  # Clean

        # Test single digit variations
        self.assertFalse(validate_nif('123456788'))  # Wrong last digit
        self.assertFalse(validate_nif('023456789'))  # Leading zero (but valid)

    def test_algorithm_correctness(self):
        """Test specific cases to verify mod11 algorithm implementation."""
        # Test case: NIF 123456789
        # Digits: [1,2,3,4,5,6,7,8,9]
        # Weights: [9,8,7,6,5,4,3,2]
        # Sum: 1*9 + 2*8 + 3*7 + 4*6 + 5*5 + 6*4 + 7*3 + 8*2 = 156
        # 156 % 11 = 2, check_digit = 11 - 2 = 9
        # Last digit is 9, so valid
        self.assertTrue(validate_nif('123456789'))

        # Test case: NIF 505956985 (business NIF)
        # This should pass validation as it's a real example
        self.assertTrue(validate_nif('505956985'))

    def test_parametrized_nifs(self):
        """Parametrized test for various NIF validation cases."""
        test_cases = [
            ('123456789', True),
            ('505956985', True),
            ('123456780', False),
            ('999999999', False),
            ('12345678', False),
            ('1234567890', False),
            ('12345678a', False),
            (' 123 456 789 ', True),
        ]

        for nif, expected in test_cases:
            self.assertEqual((nif, validate_nif(nif)), (nif, expected))
