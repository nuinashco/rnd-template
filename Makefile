.DEFAULT_GOAL := help
.PHONY: help lint test

help:  ## show targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-18s %s\n", $$1, $$2}'

lint:  ## ruff on the template's own tests
	uv run ruff check
	uv run ruff format --check

test:  ## render every variant and run its checks (NUIKIT_PATH, CONVENTIONS_PATH: local checkouts)
	uv run pytest -rs
