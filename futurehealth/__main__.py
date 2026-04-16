def main():
    try:
        from .commands.cli import CLI
    except ModuleNotFoundError as exc:
        raise SystemExit(
            'CLI dependencies are not installed. Install the package with the "cli" extra, '
            'for example: pip install "future-healthcare[cli]".'
        ) from exc

    CLI.click()


if __name__ == '__main__':
    main()
