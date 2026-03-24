import pkgutil

from . import commands


def main():
    try:
        from .commands.cli import cli
    except ModuleNotFoundError as exc:
        raise SystemExit(
            'CLI dependencies are not installed. Install the package with the "cli" extra, '
            'for example: pip install "future-healthcare-cli[cli]".'
        ) from exc

    for importer, modname, ispkg in pkgutil.iter_modules(commands.__path__):
        __import__(f'futurehealth.commands.{modname}')

    cli()


if __name__ == '__main__':
    main()
