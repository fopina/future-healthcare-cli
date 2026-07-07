from unittest.mock import MagicMock, patch

import requests

from futurehealth.client import Client, exceptions


def test_client_tls_verification_defaults_to_enabled():
    assert Client().verify is True


def test_client_can_disable_tls_verification():
    assert Client(verify=False).verify is False


def test_request_raises_structured_api_error_for_error_json_response():
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
        try:
            Client(base_url='https://example.test').get('contracts')
        except exceptions.ClientAPIError as exc:
            assert isinstance(exc, exceptions.ClientError)
            assert str(exc) == 'Contracts - Validation failed - error.api.missing_request_data (409)'
            assert exc.data == response.json.return_value
            assert exc.status_code == 409
            assert exc.response is response
            assert exc.success is False
            assert exc.result_message == 'Validation failed'
            assert exc.result_code == -108
            assert exc.result_code_detail == 'error.api.missing_request_data'
            assert exc.body == {'field': 'receipt'}
        else:
            raise AssertionError('ClientAPIError was not raised')


def test_request_raises_generic_client_error_for_non_json_error_response():
    response = MagicMock()
    response.status_code = 500
    response.json.side_effect = ValueError('not json')

    with patch.object(requests.Session, 'request', return_value=response):
        try:
            Client(base_url='https://example.test').get('contracts')
        except exceptions.ClientError as exc:
            assert type(exc) is exceptions.ClientError
            assert str(exc) == 'Unexpected error'
        else:
            raise AssertionError('ClientError was not raised')
