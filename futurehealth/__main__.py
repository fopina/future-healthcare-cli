import pkgutil

from . import commands
from .commands.cli import cli

for importer, modname, ispkg in pkgutil.iter_modules(commands.__path__):
    __import__(f'futurehealth.commands.{modname}')


if __name__ == '__main__':
    cli()
