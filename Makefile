.DEFAULT_GOAL := help
.PHONY: help lint test

# Where `make lint` gets conventions-hooks: a local checkout, else the release the template pins.
CONVENTIONS := $(or $(CONVENTIONS_PATH),git+https://github.com/nuinashco/conventions@v0.1.0)

help:  ## show targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-18s %s\n", $$1, $$2}'

lint:  ## ruff, check-comments and check-conventions on the template's own tests
	uv run ruff check
	uv run ruff format --check
	uv run --with "$(CONVENTIONS)" check-comments tests/*.py
	uv run --with "$(CONVENTIONS)" check-conventions tests/*.py

test:  ## render every variant and run its checks (NUIKIT_PATH, CONVENTIONS_PATH: local checkouts)
	uv run pytest -rs
