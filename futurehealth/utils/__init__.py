import json
import re
from pathlib import Path

from platformdirs import user_config_path

APP_NAME = 'future-healthcare-cli'
CONFIG_FILENAME = 'config.toml'
TOKEN_FILENAME = 'token.txt'


def config_path() -> Path:
    return user_config_path(APP_NAME) / CONFIG_FILENAME


def token_path() -> Path:
    return user_config_path(APP_NAME) / TOKEN_FILENAME


def parse_json_from_model(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        """try to extract from code fence"""
        match = re.search(r'```(?:json)?\s*\n(.*?)\n```', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        # re-raise original one
        raise


def validate_nif(nif: str) -> bool:
    """
    Validate Portuguese NIF (Número de Identificação Fiscal) using mod11 algorithm.

    Args:
        nif: The NIF number as a string (should be 9 digits)

    Returns:
        bool: True if NIF is valid, False otherwise

    The algorithm:
    1. NIF must be exactly 9 digits
    2. Multiply each of the first 8 digits by weights [9, 8, 7, 6, 5, 4, 3, 2]
    3. Sum the results
    4. Calculate check digit: 11 - (sum % 11)
    5. If check digit is 10, it becomes 0; if 11, it becomes 0
    6. Check digit must match the last digit of NIF
    """
    # Remove any spaces or non-digit characters
    nif = ''.join(filter(str.isdigit, nif))

    # Must be exactly 9 digits
    if len(nif) != 9:
        return False

    # All characters must be digits
    if not nif.isdigit():
        return False

    # Convert to list of integers
    digits = [int(d) for d in nif]

    # Weights for mod11 calculation
    weights = [9, 8, 7, 6, 5, 4, 3, 2]

    # Calculate weighted sum
    total = sum(d * w for d, w in zip(digits[:8], weights))

    # Calculate check digit
    check_digit = 11 - (total % 11)
    if check_digit >= 10:
        check_digit = 0

    # Check if calculated check digit matches the last digit
    return check_digit == digits[8]
