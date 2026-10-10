# Discoverable commands. `make` with no target lists them.
#
# Works in Git Bash, WSL and CI. PowerShell users: the README lists the raw
# equivalents, because a Makefile nobody can run is documentation pretending to be a
# tool.

.DEFAULT_GOAL := help
.PHONY: help bootstrap run test test-all boundaries lint fmt types check db db-stop migrate clean

help: ## list targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

bootstrap: ## install uv, then sync the locked environment
	@command -v uv >/dev/null 2>&1 || { \
		echo "installing uv..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; }
	uv sync --all-extras
	@echo
	@echo "  ready. next:  make check"

run: ## start the backend (frontend is a separate terminal)
	uv run python -m backend.app

check: lint types boundaries test ## everything CI runs, in CI's order

lint: ## ruff check + format check
	uv run ruff check .
	uv run ruff format --check .

fmt: ## apply formatting and safe fixes
	uv run ruff check --fix .
	uv run ruff format .

types: ## pyright, strict
	uv run pyright

boundaries: ## the import wall — an architectural regression test
	uv run pytest tests/test_boundaries.py -v

test: ## the suite, excluding browser/provider paths
	uv run pytest -m "not slow"

test-all: ## everything, including slow
	uv run pytest

db: ## start a local Postgres for the db-marked tests
	docker compose up -d postgres
	@echo "  waiting for postgres..."
	@until docker compose exec -T postgres pg_isready -q 2>/dev/null; do sleep 1; done
	@echo "  ready on localhost:5432"

db-stop: ## stop it
	docker compose down

migrate: ## apply migrations (runner arrives with M1)
	uv run python -m backend.store.migrate

clean: ## remove caches
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov
	find . -path ./design -prune -o -name __pycache__ -type d -print0 | xargs -0 rm -rf
