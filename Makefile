lint:
	uv run --only-group lint ruff format
	uv run --only-group lint ruff check --fix

lint-check:
	uv run --only-group lint ruff format --diff
	uv run --only-group lint ruff check

sync:
	uv sync --all-extras --dev

test:
	if [ -n "$(GITHUB_RUN_ID)" ]; then \
		uv run pytest --cov --cov-report=xml --junitxml=junit.xml -o junit_family=legacy; \
	else \
		uv run pytest --cov; \
	fi

testpub:
	rm -fr dist
	uv build
	uv run twine upload --repository testpypi dist/*
