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
- `submit` submits a new expense with receipt metadata

## Install

Install the CLI with `uv`:

```bash
uv tool install 'future-healthcare[cli]'
```

This makes the `future-healthcare` command available on your system.

If you want receipt parsing via OCR / vision models as well:

```bash
uv tool install 'future-healthcare[cli,vision]'
```

## Run Without Installing

You can also run it directly with `uvx`:

```bash
uvx --from 'future-healthcare[cli]' future-healthcare --help
```

With vision support:

```bash
uvx --from 'future-healthcare[cli,vision]' future-healthcare submit --help
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

Submit a receipt by passing the required fields explicitly:

```bash
future-healthcare submit ~/Downloads/example-receipt.pdf \
  --business-nif 509876543 \
  --invoice-number 'INV 2026/0001' \
  --total-amount 40 \
  --date '2026-03-14'
```

Or let the CLI extract those fields from the receipt with vision support:

```bash
future-healthcare submit ~/Downloads/example-receipt.pdf --vision
```

The `submit` command may prompt you to choose the insured person, service, or building when multiple matches are available.

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
openai_api_key = "..."
service = "Dentist"
vision = true

[login]
username = "YOUR_USERNAME"
```

You can also keep multiple environments in the same file and select one with `--env`:

```toml
default_env = "personal"

[submit]
openai_api_url = "https://api.venice.ai/api/v1"

[env.personal.submit]
openai_api_key = "..."

[env.work.submit]
openai_api_key = "..."
```

Then run:

```bash
future-healthcare --env work submit ~/Downloads/example-receipt.pdf --vision
```

## Local Data

The CLI stores local state under platform-specific user directories, including:

- `token.txt` for the login token
- `config.toml` for CLI defaults
- `logs/` for submission logs and copied input files

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md).
