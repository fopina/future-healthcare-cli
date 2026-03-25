import pkgutil

from . import commands


def main():
    try:
        from .commands.cli import CLI
    except ModuleNotFoundError as exc:
        print(exc)
        raise SystemExit(
            'CLI dependencies are not installed. Install the package with the "cli" extra, '
            'for example: pip install "future-healthcare[cli]".'
        ) from exc

    for importer, modname, ispkg in pkgutil.iter_modules(commands.__path__):
        __import__(f'futurehealth.commands.{modname}')

    CLI.click()


if __name__ == '__main__':
    main()
