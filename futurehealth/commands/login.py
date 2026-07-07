import classyclick
import click

from ..client import exceptions
from ..utils import token_path
from . import _mixins
from .cli import CLI


class Login(CLI.Command, _mixins.ClientMixin):
    username: str = classyclick.Option('-u', help='Username')
    password: str = classyclick.Option('-p', help='Password')

    def __call__(self):
        try:
            r = self.client.login(self.username, self.password)
        except exceptions.LoginError as e:
            raise click.ClickException(e)

        path = token_path()
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.write_text(r['body']['token'])
        print('Login succeeded')
