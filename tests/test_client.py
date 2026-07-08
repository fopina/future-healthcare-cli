import unittest
from unittest.mock import MagicMock, patch

import requests

from futurehealth.client import Client, exceptions


class TestClientRequestTimeout(unittest.TestCase):
    def success_response(self):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {'success': True}
        return response

    def test_request_uses_default_timeout(self):
        with patch.object(requests.Session, 'request', return_value=self.success_response()) as mock_request:
            Client(base_url='https://example.test').get('contracts')

        self.assertEqual(mock_request.call_args.kwargs['timeout'], 30)

    def test_request_honors_explicit_timeout(self):
        with patch.object(requests.Session, 'request', return_value=self.success_response()) as mock_request:
            Client(base_url='https://example.test').get('contracts', timeout=5)

        self.assertEqual(mock_request.call_args.kwargs['timeout'], 5)

    def test_request_can_disable_default_timeout(self):
        with patch.object(requests.Session, 'request', return_value=self.success_response()) as mock_request:
            Client(base_url='https://example.test', timeout=None).get('contracts')

        self.assertNotIn('timeout', mock_request.call_args.kwargs)


class TestClientRequestErrors(unittest.TestCase):
    def test_request_raises_structured_api_error_for_error_json_response(self):
        response = MagicMock()
        response.status_code = 409
        response.json.return_value = {
            'success': False,
            'resultMessage': 'Validation failed',
            'resultCode': -108,
            'resultCodeDetail': 'error.api.missing_request_data',
            'body': {'field': 'receipt'},
        }

        with patch.object(requests.Session, 'request', return_value=response):
            with self.assertRaises(exceptions.ClientAPIError) as raised:
                Client(base_url='https://example.test').get('contracts')

        exc = raised.exception
        self.assertIsInstance(exc, exceptions.ClientError)
        self.assertEqual(str(exc), 'Contracts - Validation failed - error.api.missing_request_data (409)')
        self.assertEqual(exc.data, response.json.return_value)
        self.assertEqual(exc.status_code, 409)
        self.assertIs(exc.response, response)
        self.assertIs(exc.success, False)
        self.assertEqual(exc.result_message, 'Validation failed')
        self.assertEqual(exc.result_code, -108)
        self.assertEqual(exc.result_code_detail, 'error.api.missing_request_data')
        self.assertEqual(exc.body, {'field': 'receipt'})

    def test_request_raises_generic_client_error_for_non_json_error_response(self):
        response = MagicMock()
        response.status_code = 500
        response.json.side_effect = ValueError('not json')

        with patch.object(requests.Session, 'request', return_value=response):
            with self.assertRaises(exceptions.ClientError) as raised:
                Client(base_url='https://example.test').get('contracts')

        self.assertIs(type(raised.exception), exceptions.ClientError)
        self.assertEqual(str(raised.exception), 'Unexpected error')
