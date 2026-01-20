# geo-extractor

A Python utility for extracting geographically-located records from Senzing JSONL files and tracking extraction statistics.

## Overview

geo-extractor provides two main tools:

1. **geo_extractor.py** - Extracts records from large JSONL source files based on geographic location (country, state, city, postal code)
2. **get_cord_stats.py** - Collects feature statistics from extracted JSONL files and updates an Excel spreadsheet

## Requirements

- Python 3.10+
- Dependencies: `openpyxl`, `orjson`

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configuration

### geo_extractor_config.json

The configuration file defines source files and target geographic regions:

```json
{
    "output_path": "../output",
    "source_files": {
        "icij": "../sources/icij-20220503.json",
        "open_sanctions": "../sources/open_sanctions-20250415.json"
    },
    "target_geos": {
        "lasvegas": {
            "countries": ["us", "usa", "united states"],
            "states": ["nv", "nevada", "us-nv"],
            "cities": ["las vegas"],
            "function": "pure_config"
        },
        "singapore": {
            "countries": ["sg", "singapore"],
            "states": [],
            "cities": ["singapore"],
            "function": "city_or_country"
        }
    }
}
```

#### Configuration Fields

| Field | Description |
|-------|-------------|
| `output_path` | Directory where extracted JSONL files are written |
| `source_files` | Map of source code names to JSONL file paths |
| `target_geos` | Map of geo names to matching criteria |

#### Geo Matching Functions

- **`pure_config`** - Matches records based on explicit city/state/postal_code values
- **`city_or_country`** - For locations where the city name equals the country name (e.g., Singapore, Malta)

## Usage

### Extracting Records by Geography

Run from the `src/` directory:

```bash
cd src

# Extract records for a single source and geo
python3 geo_extractor.py <source_code> <geo> [geo2] [geo3] ...

# Examples:
python3 geo_extractor.py icij malta
python3 geo_extractor.py open_sanctions iran iraq
python3 geo_extractor.py icij all                    # Process all configured geos
python3 geo_extractor.py all lasvegas                # Process all configured sources
```

Output files are written to `output_path` with naming format: `SOURCE-GEO.jsonl`

Example: `icij-malta.jsonl`, `open_sanctions-iran.jsonl`

### Updating Statistics Spreadsheet

After extracting records, update the statistics spreadsheet:

```bash
cd src

# Update stats for all JSONL files in a directory
python3 get_cord_stats.py <directory_or_glob_pattern>

# Examples:
python3 get_cord_stats.py ../output
python3 get_cord_stats.py "../output/icij-*.jsonl"
```

The script:
1. Reads each JSONL file (expects `SOURCE-GEO.jsonl` naming format)
2. Counts records and features by type
3. Updates or inserts rows in `_CORD_STATS.xlsx` (must exist in the target directory)
4. Sets `LAST_UPDATED` timestamp for changed rows
5. Creates a `.bak` backup before saving

### Statistics Spreadsheet Format

The `_CORD_STATS.xlsx` file tracks extraction results with these columns:

| Column | Description |
|--------|-------------|
| LAST_UPDATED | Timestamp of last update |
| SOURCE | Source code (e.g., icij, open_sanctions) |
| GEO | Geographic region (e.g., malta, iran) |
| RECORD_COUNT | Total records extracted |
| PERSON_COUNT | Records with RECORD_TYPE=PERSON |
| ORGANIZATION_COUNT | Records with RECORD_TYPE=ORGANIZATION |
| *_FEATURES | Count of each feature type (NAME, ADDRESS, PHONE, etc.) |

A sample template is provided at `samples/_CORD_STATS.xlsx`.

## Workflow Example

```bash
# 1. Configure source files and target geos in geo_extractor_config.json

# 2. Extract records for specific sources and geos
cd src
python3 geo_extractor.py icij malta moscow singapore
python3 geo_extractor.py open_sanctions iran iraq

# 3. Update statistics spreadsheet
python3 get_cord_stats.py ../output

# 4. Review results in ../output/_CORD_STATS.xlsx
```

## File Structure

```
geo-extractor/
├── src/
│   ├── geo_extractor.py           # Main extraction script
│   ├── geo_extractor_config.json  # Configuration file
│   ├── get_cord_stats.py          # Statistics collection script
│   ├── json2attribute.py          # JSON record parser
│   └── sz_default_config.json     # Senzing attribute definitions
├── samples/
│   └── _CORD_STATS.xlsx           # Sample statistics template
├── sources/                        # Source JSONL files (not included)
└── output/                         # Extracted output files
```

## License

Apache-2.0
