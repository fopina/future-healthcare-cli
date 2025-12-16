class ClientError(Exception):
    """Handled exceptions from this client"""


class LoginError(ClientError):
    """Errors during login"""
