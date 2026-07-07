import classyclick
import click

from .. import client
from ..utils import token_path
from . import _mixins
from .cli import CLI


class Login(CLI.Command, _mixins.TlsVerifyMixin):
    username: str = classyclick.Option('-u', help='Username')
    password: str = classyclick.Option('-p', help='Password')

    def __call__(self):
        client_kwargs = {}
        if self.tls_verify is False:
            client_kwargs['verify'] = False
        c = client.Client(**client_kwargs)
        try:
            r = c.login(self.username, self.password)
        except client.exceptions.LoginError as e:
            raise click.ClickException(e)

        path = token_path()
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.write_text(r['body']['token'])
        print('Login succeeded')
