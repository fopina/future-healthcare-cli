import locale as system_locale
from pathlib import Path

TOKEN_FILENAME = 'token.txt'
LOG_DIRNAME = 'logs'
ERRORS_FILENAME = 'errors.json'
SUPPORTED_LOCALES = ('pt-PT', 'en-US')
DEFAULT_LOCALE = 'en-US'


def config_dir(config_path: Path | str | None = None) -> Path:
    if config_path is not None:
        return Path(config_path).parent

    from futurehealth.commands.cli import CLI

    return CLI.CONFIG_DEFAULT_PATH.parent


def _context_value(name: str):
    try:
        import click
    except ImportError:
        return None

    ctx = click.get_current_context(silent=True)
    while ctx is not None:
        if name in ctx.meta:
            return ctx.meta[name]
        ctx = ctx.parent
    return None


def _context_path(name: str) -> Path | None:
    if context_value := _context_value(name):
        return Path(context_value)
    return None


def token_path(config_path: Path | str | None = None, override: Path | str | None = None) -> Path:
    if override is not None:
        return Path(override)
    if context_value := _context_path('token_path'):
        return context_value
    return config_dir(config_path) / TOKEN_FILENAME


def logs_path(config_path: Path | str | None = None, override: Path | str | None = None) -> Path:
    if override is not None:
        return Path(override)
    if context_value := _context_path('log_dir'):
        return context_value
    return config_dir(config_path) / LOG_DIRNAME


def errors_path(config_path: Path | str | None = None, override: Path | str | None = None) -> Path:
    if override is not None:
        return Path(override)
    if context_value := _context_path('errors_path'):
        return context_value
    return config_dir(config_path) / ERRORS_FILENAME


def normalize_locale(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.replace('_', '-')
    for supported_locale in SUPPORTED_LOCALES:
        if normalized.lower() == supported_locale.lower():
            return supported_locale
    return None


def locale(override: str | None = None) -> str:
    if override is not None:
        if normalized_locale := normalize_locale(override):
            return normalized_locale
        raise ValueError(f'Locale must be one of: {", ".join(SUPPORTED_LOCALES)}')

    if context_value := _context_path('locale'):
        return str(context_value)

    detected_locale, _ = system_locale.getlocale()
    return normalize_locale(detected_locale) or DEFAULT_LOCALE


def tls_verify(override: bool | None = None) -> bool:
    if override is not None:
        return override

    context_value = _context_value('tls_verify')
    if context_value is not None:
        return bool(context_value)

    return True


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
