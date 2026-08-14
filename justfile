# Local env file, provisioned from .env.example on `just install`
_env := ".env"

# Default recipe to run when just is called without arguments
default:
    @just --list

# Create virtual environment and install dependencies
venv:
    pip install uv
    uv venv
    source .venv/bin/activate
    @just install

# Install dependencies (provisions .env from the template on first run)
install:
    @test -f {{_env}} || cp .env.example {{_env}}
    @just install-hooks
    uv pip install -e ".[dev]"
    uv sync --all-extras

# Install git hooks (points core.hooksPath at .githooks; idempotent, safe to re-run)
install-hooks:
    git config core.hooksPath .githooks

# Update dependencies
update:
    uv pip install -e ".[dev]"
    uv lock --upgrade

# Run the integration (collect → transform → emit)
run:
    uv run python -m integration.main

# Run tests
test:
    uv run pytest

# Run all tests
test-all:
    @just test
    @just format
    @just lint
    @just typecheck

# Run linting
lint:
    uv run ruff check .
    uv run ruff format --check .

# Format code
format:
    uv run ruff format .

# Run type checking
typecheck:
    uv run basedpyright

# Create a feature branch
create-feature branch_type="feature" branch_name="" base_branch="main" update="no":
    bin/create-feature.sh {{branch_type}} {{branch_name}} {{base_branch}} {{update}}

# Clean up development artifacts
clean:
    rm -rf .pytest_cache
    rm -rf .ruff_cache
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete

# Show help
help:
    @just --list
