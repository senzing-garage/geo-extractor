# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

geo-extractor is a Python library that is part of the Senzing ecosystem. It requires Python 3.10+.

## Development Setup

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install all dependency groups
python -m pip install --group all .
```

## Common Commands

### Testing

```bash
# Run all tests with coverage
pytest tests/ --verbose --capture=no --cov=src

# Run a single test file
pytest tests/tests.py -v

# Run a specific test
pytest tests/tests.py::test_function_name -v
```

### Linting

All linters must pass for PRs. Run them before committing:

```bash
# Format code (line-length=120)
black $(git ls-files '*.py' ':!:docs/source/*')

# Sort imports
isort examples src tests

# Type checking
mypy $(git ls-files '*.py' ':!:docs/source/*')

# Lint
pylint $(git ls-files '*.py' ':!:docs/source/*')
flake8 $(git ls-files '*.py')
```

## Code Structure

- `src/` - Source code
- `tests/` - Test files (pytest)
- `pyproject.toml` - Project configuration and tool settings

## Code Style

- Line length: 120 characters
- Black for formatting with isort profile
- Type hints expected (mypy enforced)
- Follow existing pylint configuration in pyproject.toml
