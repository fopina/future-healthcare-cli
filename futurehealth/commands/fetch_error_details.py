import json
import re
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin

import classyclick
import click
import requests

from .. import client, utils
from .cli import CLI

DEFAULT_ROOT_URL = 'https://clientes-vic.future-healthcare.net/'


class ScriptSrcParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.script_srcs = []

    def handle_starttag(self, tag, attrs):
        if tag != 'script':
            return
        attrs = dict(attrs)
        if attrs.get('src'):
            self.script_srcs.append(attrs['src'])


def find_main_script_url(html, root_url):
    parser = ScriptSrcParser()
    parser.feed(html)
    for src in parser.script_srcs:
        if re.search(r'(^|/)main\.[^/]+\.js(?:\?.*)?$', src):
            return urljoin(root_url, src)
    raise click.ClickException('Could not find main.*.js script on Future Healthcare root page')


def extract_errors_array(js):
    marker = 'this.errorsListArray'
    marker_index = js.find(marker)
    if marker_index < 0:
        raise click.ClickException('Could not find this.errorsListArray in main script')

    array_start = js.find('[', marker_index)
    if array_start < 0:
        raise click.ClickException('Could not find this.errorsListArray opening bracket')

    depth = 0
    quote = None
    escaped = False
    for index in range(array_start, len(js)):
        char = js[index]
        if quote:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in ("'", '"', '`'):
            quote = char
        elif char == '[':
            depth += 1
        elif char == ']':
            depth -= 1
            if depth == 0:
                return js[array_start + 1 : index]

    raise click.ClickException('Could not find this.errorsListArray closing bracket')


def extract_error_details(js):
    errors_array = extract_errors_array(js)
    details = []
    for obj_match in re.finditer(r'\{(?P<body>.*?)\}', errors_array, re.DOTALL):
        body = obj_match.group('body')
        result_code = re.search(r'\bresultCode\s*:\s*(?P<sign>-?)\s*(?P<number>\d+)', body)
        error_message = re.search(r'\berrorMessage\s*:\s*[\'"](?P<value>[^\'"]+)[\'"]', body)
        tag = re.search(r'\btag\s*:\s*[\'"](?P<value>[^\'"]+)[\'"]', body)
        if not (result_code and error_message and tag):
            continue

        sign = -1 if result_code.group('sign') == '-' else 1
        details.append(
            {
                'resultCode': sign * int(result_code.group('number')),
                'errorMessage': error_message.group('value'),
                'tag': tag.group('value'),
            }
        )

    if not details:
        raise click.ClickException('Could not extract any error details from this.errorsListArray')
    return details


def i18n_path_for(errors_path):
    return errors_path.with_suffix('.i18n.json')


def i18n_message_for(label, i18n_labels):
    if label in i18n_labels:
        return i18n_labels[label]

    for labels in (i18n_labels, i18n_labels.get('error_details') if isinstance(i18n_labels, dict) else None):
        value = labels
        for part in label.split('.'):
            if not isinstance(value, dict) or part not in value:
                break
            value = value[part]
        else:
            return value if isinstance(value, str) else label

    return label


def strip_html_tags(value):
    return unescape(re.sub(r'<[^>]*>', '', value)).strip()


def format_error_detail(error_detail, i18n_labels):
    label = error_detail['errorMessage']
    return f'[{error_detail["resultCode"]}][{label}] {strip_html_tags(i18n_message_for(label, i18n_labels))}'


def _numeric_result_code(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _error_message_key(label):
    return label.rsplit('.', 1)[-1]


def translated_api_error_message(error: client.exceptions.ClientAPIError):
    path = utils.errors_path()
    try:
        error_details = json.loads(path.read_text())
        i18n_labels = json.loads(i18n_path_for(path).read_text())
    except (OSError, json.JSONDecodeError):
        return None

    error_details_by_code = {
        code: error_detail
        for error_detail in error_details
        if (code := _numeric_result_code(error_detail.get('resultCode'))) is not None
    }

    messages = []
    seen = set()
    for value in (error.result_code, error.result_code_detail):
        code = _numeric_result_code(value)
        if code is None:
            label = value
        else:
            error_detail = error_details_by_code.get(code)
            label = error_detail.get('errorMessage') if error_detail else None

        if not label:
            continue

        message = strip_html_tags(i18n_message_for(label, i18n_labels))
        if message == label:
            continue

        key = (code, label)
        if key in seen:
            continue
        seen.add(key)

        suffix = f'{code}, {_error_message_key(label)}' if code is not None else _error_message_key(label)
        messages.append(f'{message} ({suffix})')

    return ' '.join(messages) or None


def fetch_error_details(root_url=DEFAULT_ROOT_URL, print_errors=False):
    root_response = requests.get(root_url, timeout=30)
    root_response.raise_for_status()

    main_script_url = find_main_script_url(root_response.text, root_response.url)
    script_response = requests.get(main_script_url, timeout=30)
    script_response.raise_for_status()

    error_details = extract_error_details(script_response.text)
    path = utils.errors_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(error_details, indent=2) + '\n')

    i18n_url = urljoin(root_response.url, f'assets/i18n/{utils.locale()}.json')
    i18n_response = requests.get(i18n_url, timeout=30)
    i18n_response.raise_for_status()
    i18n_labels = i18n_response.json()
    i18n_path = i18n_path_for(path)
    i18n_path.write_text(json.dumps(i18n_labels, indent=2) + '\n')

    if print_errors:
        for error_detail in error_details:
            click.echo(format_error_detail(error_detail, i18n_labels))


def ensure_error_details_files():
    path = utils.errors_path()
    if not path.exists() or not i18n_path_for(path).exists():
        fetch_error_details()


class FetchErrorDetails(CLI.Command):
    """Fetch error codes from the Future Healthcare web UI bundle."""

    root_url: str = classyclick.Option(default=DEFAULT_ROOT_URL, help='Future Healthcare web UI root URL')

    def __call__(self):
        fetch_error_details(root_url=self.root_url, print_errors=True)
