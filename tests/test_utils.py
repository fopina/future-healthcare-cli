import pytest

from futurehealth.utils import validate_nif


class TestValidateNIF:
    """Test cases for Portuguese NIF validation using mod11 algorithm."""

    def test_valid_nifs(self):
        """Test that valid NIFs pass validation."""
        valid_nifs = [
            '123456789',  # Valid personal NIF
            '505956985',  # Valid business NIF (starts with 5)
            ' 123 456 789 ',  # Valid with spaces (should be cleaned)
        ]

        for nif in valid_nifs:
            assert validate_nif(nif), f'NIF {nif} should be valid'

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
            assert not validate_nif(nif), f'NIF {nif} should be invalid'

    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Test with various formatting
        assert validate_nif('123-456-789')  # With dashes
        assert validate_nif('123 456 789')  # With spaces
        assert validate_nif('123456789')  # Clean

        # Test single digit variations
        assert not validate_nif('123456788')  # Wrong last digit
        assert not validate_nif('023456789')  # Leading zero (but valid)

    def test_algorithm_correctness(self):
        """Test specific cases to verify mod11 algorithm implementation."""
        # Test case: NIF 123456789
        # Digits: [1,2,3,4,5,6,7,8,9]
        # Weights: [9,8,7,6,5,4,3,2]
        # Sum: 1*9 + 2*8 + 3*7 + 4*6 + 5*5 + 6*4 + 7*3 + 8*2 = 156
        # 156 % 11 = 2, check_digit = 11 - 2 = 9
        # Last digit is 9, so valid
        assert validate_nif('123456789')

        # Test case: NIF 505956985 (business NIF)
        # This should pass validation as it's a real example
        assert validate_nif('505956985')

    @pytest.mark.parametrize(
        'nif,expected',
        [
            ('123456789', True),
            ('505956985', True),
            ('123456780', False),
            ('999999999', False),
            ('12345678', False),
            ('1234567890', False),
            ('12345678a', False),
            (' 123 456 789 ', True),
        ],
    )
    def test_parametrized_nifs(self, nif, expected):
        """Parametrized test for various NIF validation cases."""
        assert validate_nif(nif) == expected
