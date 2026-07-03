class ClientError(Exception):
    """Handled exceptions from this client"""


class ClientAPIError(ClientError):
    """API error response with structured server-provided fields."""

    def __init__(self, data, status_code=None, response=None, message=None):
        self.data = data
        fields = data if isinstance(data, dict) else {}
        self.status_code = status_code
        self.response = response
        self.success = fields.get('success')
        self.result_message = fields.get('resultMessage')
        self.result_code = fields.get('resultCode')
        self.result_code_detail = fields.get('resultCodeDetail')
        self.body = fields.get('body')

        if message is None:
            message = f'{self.result_message} - {self.result_code_detail} ({status_code})'

        super().__init__(message)


class LoginError(ClientError):
    """Errors during login"""
