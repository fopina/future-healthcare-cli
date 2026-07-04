import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, call, patch

from click.testing import CliRunner

from futurehealth.client import exceptions
from futurehealth.commands.cli import CLI
from futurehealth.commands.fetch_error_details import (
    FetchErrorDetails,
    ensure_error_details_files,
    extract_error_details,
    fetch_error_details,
    find_main_script_url,
    format_error_detail,
    i18n_message_for,
    i18n_path_for,
    strip_html_tags,
    translated_api_error_message,
)

FIXTURES = Path(__file__).parent / 'fixtures'


class TestFetchErrorDetails(unittest.TestCase):
    def test_find_main_script_url(self):
        html = """
        <html>
          <script src="/runtime.123.js"></script>
          <script src="/static/js/main.abc123.js"></script>
        </html>
        """

        self.assertEqual(
            find_main_script_url(html, 'https://clientes-vic.future-healthcare.net/app/'),
            'https://clientes-vic.future-healthcare.net/static/js/main.abc123.js',
        )

    def test_extract_error_details(self):
        js = """
        this.errorsListArray = [
          {
            resultCode: - 108,
            errorMessage: 'error.api.missing_request_data',
            tag: 'MISSING_REQUEST_DATA'
          },
          {
            resultCode: 12,
            errorMessage: "error.api.other",
            tag: "OTHER"
          }
        ];
        """

        self.assertEqual(
            extract_error_details(js),
            [
                {
                    'resultCode': -108,
                    'errorMessage': 'error.api.missing_request_data',
                    'tag': 'MISSING_REQUEST_DATA',
                },
                {
                    'resultCode': 12,
                    'errorMessage': 'error.api.other',
                    'tag': 'OTHER',
                },
            ],
        )

    def test_i18n_path_for_errors_path(self):
        self.assertEqual(
            i18n_path_for(Path('/tmp/cache/errors.json')),
            Path('/tmp/cache/errors.i18n.json'),
        )

    def test_i18n_message_for_flat_label(self):
        self.assertEqual(
            i18n_message_for(
                'error.api.missing_request_data',
                {'error.api.missing_request_data': 'Missing request data'},
            ),
            'Missing request data',
        )

    def test_i18n_message_for_nested_label(self):
        self.assertEqual(
            i18n_message_for(
                'error.api.missing_request_data',
                {'error': {'api': {'missing_request_data': 'Missing request data'}}},
            ),
            'Missing request data',
        )

    def test_i18n_message_for_missing_label_falls_back_to_label(self):
        self.assertEqual(
            i18n_message_for(
                'error.api.missing_request_data',
                {'error': {'api': {}}},
            ),
            'error.api.missing_request_data',
        )

    def test_strip_html_tags(self):
        self.assertEqual(
            strip_html_tags('Missing <strong>request</strong> data&nbsp;now'),
            'Missing request data\xa0now',
        )

    def test_format_error_detail(self):
        self.assertEqual(
            format_error_detail(
                {
                    'resultCode': -108,
                    'errorMessage': 'error.api.missing_request_data',
                    'tag': 'MISSING_REQUEST_DATA',
                },
                {'error.api.missing_request_data': 'Missing request data'},
            ),
            '[-108][error.api.missing_request_data] Missing request data',
        )

    def test_format_error_detail_strips_html_tags(self):
        self.assertEqual(
            format_error_detail(
                {
                    'resultCode': -108,
                    'errorMessage': 'error.api.missing_request_data',
                    'tag': 'MISSING_REQUEST_DATA',
                },
                {'error': {'api': {'missing_request_data': 'Missing <strong>request</strong> data'}}},
            ),
            '[-108][error.api.missing_request_data] Missing request data',
        )

    def test_format_error_detail_resolves_nested_i18n_labels(self):
        self.assertEqual(
            format_error_detail(
                {
                    'resultCode': -108,
                    'errorMessage': 'error.api.missing_request_data',
                    'tag': 'MISSING_REQUEST_DATA',
                },
                {'error': {'api': {'missing_request_data': 'Missing request data'}}},
            ),
            '[-108][error.api.missing_request_data] Missing request data',
        )

    def test_format_error_detail_falls_back_to_label(self):
        self.assertEqual(
            format_error_detail(
                {
                    'resultCode': -108,
                    'errorMessage': 'error.api.missing_request_data',
                    'tag': 'MISSING_REQUEST_DATA',
                },
                {},
            ),
            '[-108][error.api.missing_request_data] error.api.missing_request_data',
        )

    def test_translated_api_error_message_uses_cached_error_details_fixture(self):
        error = exceptions.ClientAPIError(
            {
                'resultMessage': 'Validation failed',
                'resultCodeDetail': -473,
            }
        )

        with patch(
            'futurehealth.commands.fetch_error_details.utils.errors_path',
            return_value=FIXTURES / 'future-health-errors-473.json',
        ):
            self.assertEqual(
                translated_api_error_message(error),
                "We're sorry, but the reimbursement submission deadline has expired.",
            )

    def test_translated_api_error_message_returns_none_when_cache_misses(self):
        with TemporaryDirectory() as tmp:
            errors_path = Path(tmp) / 'errors.json'
            errors_path.write_text('[]')
            i18n_path_for(errors_path).write_text('{}')
            error = exceptions.ClientAPIError({'resultCode': -108, 'resultCodeDetail': 'error.api.missing'})

            with patch('futurehealth.commands.fetch_error_details.utils.errors_path', return_value=errors_path):
                self.assertIsNone(translated_api_error_message(error))

    @patch('futurehealth.commands.fetch_error_details.fetch_error_details')
    def test_ensure_error_details_files_fetches_when_errors_file_is_missing(self, mock_fetch):
        with TemporaryDirectory() as tmp:
            errors_path = Path(tmp) / 'errors.json'

            with patch('futurehealth.commands.fetch_error_details.utils.errors_path', return_value=errors_path):
                ensure_error_details_files()

        mock_fetch.assert_called_once_with()

    @patch('futurehealth.commands.fetch_error_details.fetch_error_details')
    def test_ensure_error_details_files_fetches_when_i18n_file_is_missing(self, mock_fetch):
        with TemporaryDirectory() as tmp:
            errors_path = Path(tmp) / 'errors.json'
            errors_path.write_text('[]')

            with patch('futurehealth.commands.fetch_error_details.utils.errors_path', return_value=errors_path):
                ensure_error_details_files()

        mock_fetch.assert_called_once_with()

    @patch('futurehealth.commands.fetch_error_details.fetch_error_details')
    def test_ensure_error_details_files_skips_fetch_when_cache_exists(self, mock_fetch):
        with TemporaryDirectory() as tmp:
            errors_path = Path(tmp) / 'errors.json'
            errors_path.write_text('[]')
            i18n_path_for(errors_path).write_text('{}')

            with patch('futurehealth.commands.fetch_error_details.utils.errors_path', return_value=errors_path):
                ensure_error_details_files()

        mock_fetch.assert_not_called()

    @patch('futurehealth.commands.fetch_error_details.requests.get')
    def test_command_fetches_main_script_and_writes_default_errors_file(self, mock_get):
        root_response = MagicMock()
        root_response.text = '<script src="/main.abc123.js"></script>'
        root_response.url = 'https://clientes-vic.future-healthcare.net/'
        script_response = MagicMock()
        script_response.text = """
        this.errorsListArray = [
          { resultCode: - 108, errorMessage: 'error.api.missing_request_data', tag: 'MISSING_REQUEST_DATA' }
        ];
        """
        i18n_response = MagicMock()
        i18n_response.json.return_value = {'error': {'api': {'missing_request_data': 'Missing request data'}}}
        mock_get.side_effect = [root_response, script_response, i18n_response]

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / 'config.toml'
            config_path.write_text('')
            errors_path = tmp_path / 'errors.json'
            i18n_path = tmp_path / 'errors.i18n.json'

            result = CliRunner().invoke(
                CLI.click,
                ['--config', str(config_path), '--locale', 'en-US', 'fetch-error-details'],
            )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertEqual(
                result.output,
                '[-108][error.api.missing_request_data] Missing request data\n',
            )
            self.assertEqual(
                json.loads(errors_path.read_text()),
                [
                    {
                        'resultCode': -108,
                        'errorMessage': 'error.api.missing_request_data',
                        'tag': 'MISSING_REQUEST_DATA',
                    }
                ],
            )
            self.assertEqual(
                json.loads(i18n_path.read_text()),
                {'error': {'api': {'missing_request_data': 'Missing request data'}}},
            )
        self.assertEqual(
            mock_get.mock_calls,
            [
                call('https://clientes-vic.future-healthcare.net/', timeout=30),
                call('https://clientes-vic.future-healthcare.net/main.abc123.js', timeout=30),
                call('https://clientes-vic.future-healthcare.net/assets/i18n/en-US.json', timeout=30),
            ],
        )
        root_response.raise_for_status.assert_called_once_with()
        script_response.raise_for_status.assert_called_once_with()
        i18n_response.raise_for_status.assert_called_once_with()

    @patch('futurehealth.commands.fetch_error_details.requests.get')
    def test_group_errors_path_option_controls_output_file(self, mock_get):
        root_response = MagicMock()
        root_response.text = '<script src="/main.abc123.js"></script>'
        root_response.url = 'https://clientes-vic.future-healthcare.net/'
        script_response = MagicMock()
        script_response.text = """
        this.errorsListArray = [
          { resultCode: 12, errorMessage: 'error.api.other', tag: 'OTHER' }
        ];
        """
        i18n_response = MagicMock()
        i18n_response.json.return_value = {'error': {'api': {'other': 'Other'}}}
        mock_get.side_effect = [root_response, script_response, i18n_response]

        with TemporaryDirectory() as tmp:
            errors_path = Path(tmp) / 'cache' / 'future-health-errors.json'

            result = CliRunner().invoke(
                CLI.click,
                ['--errors-path', str(errors_path), '--locale', 'pt-PT', 'fetch-error-details'],
            )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertEqual(result.output, '[12][error.api.other] Other\n')
            self.assertEqual(
                json.loads(errors_path.read_text()),
                [{'resultCode': 12, 'errorMessage': 'error.api.other', 'tag': 'OTHER'}],
            )
            self.assertEqual(
                json.loads((Path(tmp) / 'cache' / 'future-health-errors.i18n.json').read_text()),
                {'error': {'api': {'other': 'Other'}}},
            )
        mock_get.assert_has_calls(
            [
                call('https://clientes-vic.future-healthcare.net/', timeout=30),
                call('https://clientes-vic.future-healthcare.net/main.abc123.js', timeout=30),
                call('https://clientes-vic.future-healthcare.net/assets/i18n/pt-PT.json', timeout=30),
            ]
        )

    @patch('futurehealth.commands.fetch_error_details.requests.get')
    def test_fetch_error_details_can_run_without_printing_errors(self, mock_get):
        root_response = MagicMock()
        root_response.text = '<script src="/main.abc123.js"></script>'
        root_response.url = 'https://clientes-vic.future-healthcare.net/'
        script_response = MagicMock()
        script_response.text = """
        this.errorsListArray = [
          { resultCode: 12, errorMessage: 'error.api.other', tag: 'OTHER' }
        ];
        """
        i18n_response = MagicMock()
        i18n_response.json.return_value = {'error': {'api': {'other': 'Other'}}}
        mock_get.side_effect = [root_response, script_response, i18n_response]

        with TemporaryDirectory() as tmp:
            errors_path = Path(tmp) / 'errors.json'
            with (
                patch('futurehealth.commands.fetch_error_details.utils.errors_path', return_value=errors_path),
                patch('futurehealth.commands.fetch_error_details.click.echo') as echo,
            ):
                fetch_error_details()

            self.assertEqual(
                json.loads(errors_path.read_text()),
                [{'resultCode': 12, 'errorMessage': 'error.api.other', 'tag': 'OTHER'}],
            )
            self.assertEqual(json.loads(i18n_path_for(errors_path).read_text()), {'error': {'api': {'other': 'Other'}}})
            echo.assert_not_called()

    def test_cli_registers_fetch_error_details_command(self):
        self.assertIs(CLI.click.commands['fetch-error-details'], FetchErrorDetails.click)
