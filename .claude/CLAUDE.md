# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

geo-extractor is a Python library for extracting geographically-located records from JSONL files. It parses Senzing-formatted JSON records and filters them based on configurable geographic criteria (countries, states, cities, postal codes). Part of the Senzing ecosystem, requires Python 3.10+.

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m pip install --group test .
```

## Common Commands

### Testing

```bash
pytest tests/ --verbose --capture=no --cov=src
pytest tests/geo_extractor_example_test.py -v
pytest tests/geo_extractor_example_test.py::test_function_name -v
```

### Linting

All linters must pass for PRs:

```bash
black $(git ls-files '*.py' ':!:docs/source/*')
isort examples src tests
mypy $(git ls-files '*.py' ':!:docs/source/*')
pylint $(git ls-files '*.py' ':!:docs/source/*')
flake8 $(git ls-files '*.py')
```

## Architecture

### Core Components

- **`src/geo_extractor.py`** - Main CLI tool that extracts records from JSONL source files based on geographic filtering rules. Reads configuration from `geo_extractor_config.json`.

- **`src/json2attribute.py`** - `json2attribute` class that parses Senzing JSON records into normalized attribute lists. Loads attribute/feature definitions from `sz_default_config.json`.

- **`src/get_cord_stats.py`** - Utility script that collects feature statistics from JSONL files (named `SOURCE-GEO.jsonl`) and updates `_CORD_STATS.xlsx` spreadsheet. Tracks record counts, feature counts by type, and record type counts. Updates existing rows by SOURCE+GEO or inserts new rows preserving formatting.

### Configuration Files

- **`src/geo_extractor_config.json`** - Defines source files to process and target geo rules. Each geo entry specifies countries, states, cities, postal_codes arrays and a matching function name.

- **`src/sz_default_config.json`** - Senzing default configuration containing `CFG_ATTR` (attribute definitions) and `CFG_FTYPE` (feature type definitions).

### Geographic Matching Functions

The geo extractor uses two matching strategies (defined in `geo_extractor.py`):

- **`pure_config()`** - Matches based on explicit city/state/postal_code configuration
- **`city_or_country()`** - For geos where the city name equals the country name (e.g., Singapore, Malta)

Both functions check `ADDR_FULL` (single-line address) or individual address components (`ADDR_CITY`, `ADDR_STATE`, `ADDR_POSTAL_CODE`, `ADDR_COUNTRY`).

### Data Flow

1. `geo_extractor.py` loads config and iterates through source JSONL files
2. Each line is parsed via `json2attribute.parse()` which returns attribute list
3. ADDRESS attributes are extracted and tested against configured geo rules
4. Matching records are written to geo-specific output files

## Code Style

- Line length: 120 characters
- Black formatting with isort profile
- Type hints expected (mypy enforced)
