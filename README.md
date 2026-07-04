# future-healthcare-cli

[![ci](https://github.com/fopina/future-healthcare-cli/actions/workflows/publish-main.yml/badge.svg)](https://github.com/fopina/future-healthcare-cli/actions/workflows/publish-main.yml)
[![test](https://github.com/fopina/future-healthcare-cli/actions/workflows/test.yml/badge.svg)](https://github.com/fopina/future-healthcare-cli/actions/workflows/test.yml)
[![codecov](https://codecov.io/github/fopina/future-healthcare-cli/graph/badge.svg)](https://codecov.io/github/fopina/future-healthcare-cli)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/future-healthcare.svg)](https://pypi.org/project/future-healthcare/)
[![Current version on PyPI](https://img.shields.io/pypi/v/future-healthcare)](https://pypi.org/project/future-healthcare/)
[![Very popular](https://img.shields.io/pypi/dm/future-healthcare)](https://pypistats.org/packages/future-healthcare)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Python library and optional CLI for Future Healthcare.

The CLI helps with common refund flows:

- `login` stores your API token locally
- `check` lists refund status/history
- `nifs` looks up known refund addresses for a business NIF
- `submit` submits a new expense with receipt metadata

## Install

Install the CLI with `uv`:

```bash
uv tool install 'future-healthcare[cli]'
```

This makes the `future-healthcare` command available on your system.

## Run Without Installing

You can also run it directly with `uvx`:

```bash
uvx --from 'future-healthcare[cli]' future-healthcare --help
```

## Usage

Log in first:

```bash
future-healthcare login -u YOUR_USERNAME -p YOUR_PASSWORD
```

Check existing refunds:

```bash
future-healthcare check
```

Look up the available addresses for a business NIF:

```bash
future-healthcare nifs 509876543
```

Submit a receipt by passing the required fields explicitly:

```bash
future-healthcare submit ~/Downloads/example-receipt.pdf \
  --business-nif 509876543 \
  --invoice-number 'INV 2026/0001' \
  --total-amount 40 \
  --date '2026-03-14'
```

The `submit` command may prompt you to choose the insured person, service, or building when multiple matches are available.
Use `--address-number` to select a building/address up front for non-interactive runs; the number matches the output
from `future-healthcare nifs`.
Receipt data extraction happens before calling the CLI. Agent users can use the bundled Codex skill in
`.agents/skills/future-healthcare-cli/SKILL.md` to inspect the receipt, extract the required fields, and then run
`future-healthcare submit` with explicit flags.

## Configuration

The CLI reads defaults from ClassyClick's default `config.toml` location.
You can inspect the active configuration and its file path with:

```bash
future-healthcare config
```

To edit it in `$VISUAL` or `$EDITOR`:

```bash
future-healthcare config --edit
```

Configuration mirrors the CLI command options:

```toml
[submit]
service = "Dentist"

[login]
username = "YOUR_USERNAME"
```

You can also keep multiple environments in the same file and select one with `--env`:

```toml
default_env = "personal"

[submit]
service = "Dentist"

[env.personal.submit]
person = "Alice"

[env.work.submit]
person = "Bob"
```

Then run:

```bash
future-healthcare --env work submit ~/Downloads/example-receipt.pdf \
  --business-nif 509876543 \
  --invoice-number 'INV 2026/0001' \
  --total-amount 40 \
  --date '2026-03-14'
```

Use group-level path flags when you want local state somewhere else:

```bash
future-healthcare --token-path ~/.future-healthcare/token.txt --log-dir ~/.future-healthcare/logs login \
  -u YOUR_USERNAME \
  -p YOUR_PASSWORD
```

## Local Data

By default, the CLI stores local state next to the selected configuration file, including:

- `token.txt` for the login token
- `config.toml` for CLI defaults
- `logs/` for submission logs and copied input files

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md).
