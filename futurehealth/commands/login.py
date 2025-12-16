import classyclick
import click

from ..client import Client
from .cli import cli
from ..utils import token_path


@classyclick.command(group=cli)
class Login:
    username: str = classyclick.Option('-u', help='Username')
    password: str = classyclick.Option('-p', help='Password')

    def __call__(self):
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
