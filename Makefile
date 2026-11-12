.DEFAULT_GOAL := help
.PHONY: help lint test

# Where `make lint` gets conventions-hooks: a local checkout as it is on disk, else the release the
# template pins in copier.yml (a test keeps the two tags equal).
CONVENTIONS := $(if $(CONVENTIONS_PATH),--with-editable "$(CONVENTIONS_PATH)",--with git+https://github.com/nuinashco/conventions@v0.1.0)

help:  ## show targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-18s %s\n", $$1, $$2}'

lint:  ## ruff, check-comments and check-conventions on the template's own Python
	uv run ruff check
	uv run ruff format --check
	uv run $(CONVENTIONS) check-comments tests/*.py migrations/*.py
	uv run $(CONVENTIONS) check-conventions tests/*.py migrations/*.py

test:  ## render every variant and run its checks (NUIKIT_PATH, CONVENTIONS_PATH: local checkouts)
	uv run pytest -rs
