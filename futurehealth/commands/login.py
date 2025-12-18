import classyclick
import click

from .. import client
from ..utils import token_path
from .cli import cli


@classyclick.command(group=cli)
class Login:
    username: str = classyclick.Option('-u', help='Username')
    password: str = classyclick.Option('-p', help='Password')

    def __call__(self):
        c = client.Client()
        try:
            r = c.login(self.username, self.password)
        except client.exceptions.LoginError as e:
            raise click.ClickException(e)

        path = token_path()
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.write_text(r['body']['token'])
        print('Login succeeded')
