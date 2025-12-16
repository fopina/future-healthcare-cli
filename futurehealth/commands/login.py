from classyclick import command

from .cli import cli


@command(group=cli)
class Login:
    def __call__(self):
        print('asd')
