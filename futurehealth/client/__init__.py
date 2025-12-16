import requests

from . import exceptions


class Client(requests.Session):
    """HTTP Client for Future Healthcare API.

    Inherits from requests.Session to provide connection pooling
    and persistent configuration across requests.
    """

    def __init__(self, base_url=None, partnership='vic', *args, **kwargs):
        """Initialize the Client.

        Args:
            base_url: Optional base URL for API requests
            partnership: Partnership identifier (default: 'vic')
            *args: Additional positional arguments for requests.Session
            **kwargs: Additional keyword arguments for requests.Session
        """
        super().__init__(*args, **kwargs)
        self.base_url = base_url
        self.partnership = partnership

    def request(self, method, url, *args, **kwargs):
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
            url = f'{self.base_url.rstrip("/")}/{url.lstrip("/")}'
        return super().request(method, url, *args, **kwargs)

    def login(self, username, password) -> dict:
        """Login to Future Healthcare API."""
        url = 'https://ws.future-healthcare.net/prd/api/fhc/fhcp/login'

        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Partnership': self.partnership,
        }

        payload = {'username': username, 'password': password}

        r = self.post(url, json=payload, headers=headers)
        if r.status_code != 200:
            try:
                rd = r.json()
                exc = exceptions.LoginError(f'{rd["resultMessage"]} ({r.status_code})')
            except Exception:
                exc = exceptions.LoginError('Unexpected error')
            raise exc

        r = r.json()
        if not r['success']:
            raise exceptions.LoginError('Unexpected!! Status 200 without success??')
        return r
