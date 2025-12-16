import classyclick
import click

from ..client import Client
from ..utils import token_path
from .cli import cli


@classyclick.command(group=cli)
class Submit:
    def __call__(self):
        path = token_path()
        token = path.read_text()
        c = Client()
        r = c.login(self.username, self.password)
        if r.status_code != 401:
            # 401 to be json-parsed as well
            r.raise_for_status()
        r = r.json()
        if not r['success']:
            raise click.ClickException(f'Login failed - {r["resultMessage"]}')
        path = token_path()
        path.parent.mkdir(parents=True, exist_ok=True, mode=700)
        path.write_text(r['body']['token'])
        print('Login succeeded')
