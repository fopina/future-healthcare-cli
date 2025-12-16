from urllib.parse import quote

import requests

from . import exceptions


class Client(requests.Session):
    """HTTP Client for Future Healthcare API.

    Inherits from requests.Session to provide connection pooling
    and persistent configuration across requests.
    """

    def __init__(
        self,
        base_url='https://ws.future-healthcare.net/prd/api/fhc/fhcp/',
        token=None,
        partnership='vic',
        *args,
        **kwargs,
    ):
        """Initialize the Client.

        Args:
            base_url: Optional base URL for API requests
            partnership: Partnership identifier (default: 'vic')
            *args: Additional positional arguments for requests.Session
            **kwargs: Additional keyword arguments for requests.Session
        """
        super().__init__(*args, **kwargs)
        self.base_url = base_url.rstrip('/')
        self.partnership = partnership
        self.token = token

    def request(self, method, url, *args, _token=False, headers=None, **kwargs):
        """Make an HTTP request.

        If base_url is set and url is relative, prepends base_url to the URL.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: URL or path for the request
            *args: Additional positional arguments for requests.Session.request
            **kwargs: Additional keyword arguments for requests.Session.request

        Returns:
            requests.Response object
        """
        if self.base_url and not url.startswith(('http://', 'https://')):
            url = f'{self.base_url}/{url.lstrip("/")}'
            if headers is None:
                kwargs['headers'] = {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'X-Partnership': self.partnership,
                }
            else:
                kwargs['headers'] = headers
            if _token:
                kwargs['headers']['Authorization'] = f'Bearer {self.token}'
        r = super().request(method, url, *args, **kwargs)
        if r.status_code != 200:
            try:
                rd = r.json()
                exc = exceptions.ClientError(f'Contracts - {rd["resultMessage"]} ({r.status_code})')
            except Exception:
                exc = exceptions.ClientError('Unexpected error')
            raise exc

        r = r.json()
        if not r['success']:
            raise exceptions.ClientError('Unexpected!! Status 200 without success??')
        return r

    def login(self, username, password) -> dict:
        """Login."""

        payload = {'username': username, 'password': password}

        try:
            r = self.post('login', json=payload)
        except exceptions.ClientError as e:
            raise exceptions.LoginError(str(e))

        self.token = r['body']['token']
        return r

    def contracts(self) -> dict:
        """Retrieve contracts for the current account."""

        r = self.get('contracts', _token=True)
        return r['body']['Contracts']

    def validate_feature(self, contract_token: str, feature: str) -> bool:
        """Validate that contract has feature."""

        r = self.post(
            f'contracts/{quote(contract_token, safe="")}/validate-feature', _token=True, json={'feature': feature}
        )
        return r['body']['valid']

    def refunds_request_setup(self, contract_token: str) -> bool:
        """Validate that contract has feature."""

        r = self.get(f'contracts/{quote(contract_token, safe="")}/refunds-requests/setup', _token=True)
        return r['body']
