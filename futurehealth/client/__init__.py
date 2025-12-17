import random
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import requests

from . import exceptions, models


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
        language='pt-PT',
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
        self.language = language
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
                headers = {}
            headers['X-Partnership'] = self.partnership
            headers['X-Partnershipapilink'] = self.partnership
            headers['X-Language'] = self.language
            if _token:
                headers['Authorization'] = f'Bearer {self.token}'
        r = super().request(method, url, *args, headers=headers, **kwargs)
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

    def files(self, path: Path, is_invoice=False):
        """Upload a file to the files endpoint.

        Args:
            path: Path to the file to upload

        Returns:
            dict: Response from the server
        """
        if not path.exists():
            raise exceptions.ClientError(f'File not found: {path}')

        with path.open('rb') as f:
            files = {'filename': (path.name, f, 'application/pdf')}
            r = self.post('files', files=files, _token=True, headers={'X-Isinvoice': 'true' if is_invoice else 'false'})

        return r['body']


@dataclass
class RefundsRequestSetupResponse:
    services: list[models.Service]
    insured_persons: list[models.Person]
    other: dict


class ContractClient(requests.Session):
    def __init__(
        self,
        client: Client,
        contract_token: str,
        *args,
        **kwargs,
    ):
        """Initialize a client for contract-specific endpoints."""
        super().__init__(*args, **kwargs)
        self._client = client
        self._contract_token = contract_token

    def request(self, method: str, url: str, *args, **kwargs):
        if not url.startswith(('http://', 'https://')):
            url = f'contracts/{quote(self._contract_token, safe="")}/{url.lstrip("/")}'
        return self._client.request(method, url, *args, _token=True, **kwargs)

    def validate_feature(self, feature: str) -> bool:
        """Validate that contract has feature."""

        r = self.post('validate-feature', json={'feature': feature})
        return r['body']['valid']

    def refunds_request_setup(self) -> RefundsRequestSetupResponse:
        """Validate that contract has feature."""

        r = self.get('refunds-requests/setup')
        data = r['body']
        services = [models.Service(**obj) for obj in data['Services']]
        ip = [models.Person(**obj) for obj in data['InsuredPersons']]
        del data['Services']
        del data['InsuredPersons']
        return RefundsRequestSetupResponse(services, ip, data)

    def unified_refunds(self, page_size=5, page=1) -> bool:
        """Validate that contract has feature."""

        r = self.get(
            'unified-refunds',
            params={'page': page, 'pageSize': page_size},
        )
        return r['body']

    def load_buildings(self, nif: str) -> list[models.Building]:
        """Validate that contract has feature."""

        r = self.post(
            'refunds-requests/loadBuildings',
            json={'practiceNif': nif},
        )
        return [models.Building(**building) for building in r['body']['buildings']]

    def multiple_refunds_requests(
        self,
        card_number: str,
        service_id: str,
        nif: str,
        receipt: str,
        total: float,
        treatment_date: str,
        docs: list[str],
        primary_entity: bool,
        accident: bool,
        building: str,
        email: str,
    ) -> bool:
        """Validate that contract has feature."""

        payload = {
            'refundSubmissions': [
                {
                    'CardNumber': card_number,
                    'ServiceId': service_id,
                    'NationalPractice': True,
                    'PracticeFiscalNumber': nif,
                    'practiceFiscalNumberPrefix': 'PT',
                    'ReceiptNumber': receipt,
                    'TotalValue': total,
                    'DateOfTreatment': treatment_date,
                    'DocumentGuidList': docs,
                    'IsPrimaryEntity': primary_entity,
                    'IsAccident': accident,
                    'IsInternalNetwork': True,
                    'MeanOfPayment': 'IBAN',
                    'PhonePrefix': '+351',
                    'originId': int(random.random() * 9999),
                    'BuildingId': building,
                    'Email': email,
                }
            ]
        }
        # nothing to return - "success" and errors already checked by self.request
        self.post('multiple-refunds-requests', json=payload)
