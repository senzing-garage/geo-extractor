#!/usr/bin/env python3
"""Extract geographically-located records from Senzing JSONL files."""
import argparse
import json
import os
import re
import sys
import time

from json2attribute import json2attribute

APP_PATH = os.path.dirname(__file__) + os.path.sep
SENZING_CONFIG_FILE = APP_PATH + "sz_default_config.json"
APP_CONFIG_FILE = APP_PATH + "geo_extractor_config.json"

json_parser = json2attribute(SENZING_CONFIG_FILE)


class JSONWithComments(json.JSONDecoder):
    """Remove comments from a JSON file"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def decode(self, json_string: str):
        regex = r"""("(?:\\"|[^"])*?")|(\/\*(?:.|\s)*?\*\/|\/\/.*)"""
        json_string = re.sub(regex, r"\1", json_string)
        return super().decode(json_string)


# Read the JSON file containing configuration for geos
try:
    with open(APP_CONFIG_FILE, "r", encoding="utf-8") as file:
        config = json.loads(file.read(), cls=JSONWithComments)
        output_path = config["output_path"]
        source_files = config["source_files"]
        GEOS = {k: config["target_geos"][k] for k in config["target_geos"].keys() if not k.startswith("inactive")}
except (OSError, json.JSONDecodeError) as err:
    print(f"\nERROR: {err}", flush=True)
    sys.exit(1)

# Add space padded versions to the GEOS dictionary
for k in GEOS:
    GEOS[k]["states_pad"] = [f" {s} " for s in GEOS[k]["states"]]
    GEOS[k]["cities_pad"] = [f" {c} " for c in GEOS[k]["cities"]]

CONFIGURED_GEOS = list(GEOS)
CHOICES_GEOS = CONFIGURED_GEOS.copy()
CHOICES_GEOS.append("all")
VALID_RECORD_TYPES = ("PERSON", "ORGANIZATION")


def pure_config(geo, addr_data):
    """Match address against geo config using explicit city/state/postal_code values."""
    any_city = len(GEOS[geo].get("cities", [])) == 0
    any_state = len(GEOS[geo].get("states", [])) == 0
    any_postal = len(GEOS[geo].get("postal_codes", [])) == 0

    if addr_data["HAS_ADDR_FULL"]:
        if any_city or any(s in addr_data["ADDR_FULL"] for s in GEOS[geo]["cities_pad"]):
            if any_state or any(s in addr_data["ADDR_FULL"] for s in GEOS[geo]["states_pad"]):
                if any_postal or any(f" {s}" in addr_data["ADDR_FULL"] for s in GEOS[geo]["postal_codes"]):
                    return True
        return False

    if any_city or any(addr_data["ADDR_CITY"] == s for s in GEOS[geo]["cities"]):
        if any_state or any(addr_data["ADDR_STATE"] == s for s in GEOS[geo]["states"]):
            if any_postal or any(addr_data["ADDR_POSTAL_CODE"].startswith(s) for s in GEOS[geo]["postal_codes"]):
                return True

    return False


def city_or_country(geo, addr_data):
    """Used for geos where the city is also a country and the geo might be in either addr_city or addr_country"""
    if addr_data["HAS_ADDR_FULL"]:
        return any(c in addr_data["ADDR_FULL"] for c in GEOS[geo]["cities_pad"])
    return any(s in addr_data["ADDR_CITY"] for s in GEOS[geo]["cities"]) or any(
        c in addr_data["ADDR_COUNTRY"] for c in GEOS[geo]["countries"]
    )


def confirm_country(target_geo, addr_data):
    """Verify address country matches the target geo's configured countries."""
    if addr_data["ADDR_COUNTRY"]:
        in_country = any(addr_data["ADDR_COUNTRY"] == c for c in GEOS[target_geo]["countries"])
    elif addr_data["HAS_ADDR_FULL"]:
        in_country = any(f" {c} " in addr_data["ADDR_FULL"] for c in GEOS[target_geo]["countries"])
    else:
        in_country = not addr_data["ADDR_COUNTRY"]
    if not in_country:
        if target_geo not in invalid_country_log:
            invalid_country_log[target_geo] = {}
        bad_value = f"{addr_data['ADDR_CITY']}, {addr_data['ADDR_STATE']}, {addr_data['ADDR_COUNTRY']}"
        if bad_value not in invalid_country_log[target_geo]:
            invalid_country_log[target_geo][bad_value] = 1
        else:
            invalid_country_log[target_geo][bad_value] += 1
    return in_country


arg_parser = argparse.ArgumentParser(
    allow_abbrev=False,
    description="Utility to extract geo located records from JSONL files",
    formatter_class=argparse.RawTextHelpFormatter,
)
arg_parser.add_argument(
    "source_file", nargs="?", help="input file to extract JSONL records from. Use all to process all files."
)
arg_parser.add_argument(
    "target_geos",
    choices=CHOICES_GEOS,
    metavar="target_geos",
    nargs="+",
    help=f"one or more (space separated) target geos. Use all to process all geos. Available geos:\n{', '.join(CHOICES_GEOS)}",
)
arg_parser.add_argument(
    "-o",
    default=100_000,
    dest="output_frequency",
    metavar="int",
    nargs=1,
    type=int,
    help="change stats output frequency, default = %(default)s",
)
arg_parser.add_argument("-a", "--alpha", dest="alpha_filter", default="", help="optional name startswith filter")
arg_parser.add_argument("-D", "--debug", dest="debug", action="store_true", default=False, help="run in debug mode")

cli_args = arg_parser.parse_args()
source_file = cli_args.source_file
target_geos = cli_args.target_geos
if len(cli_args.target_geos) == 1 and "all" in cli_args.target_geos:
    target_geos = CONFIGURED_GEOS
MAX_GEO_LEN = len(max(target_geos, key=len))
target_stats = {}
invalid_country_log = {}

if source_file.lower() != "all":
    if source_file not in source_files:
        print(f"\n{source_file} not configured, configured files:\n")
        for sf in source_files:
            print(f"\t{sf}")
        sys.exit(1)
    source_files = {source_file: source_files[source_file]}

# print("sources", source_files.keys)
# print("geos", target_geos)

cli_args.alpha_filter = cli_args.alpha_filter.lower()
alpha_extension = f"-{cli_args.alpha_filter.upper()}" if cli_args.alpha_filter else ""

for source_code, source_file in source_files.items():
    target_stats[source_code] = {}
    for tg in target_geos:
        target_stats[source_code][tg] = {
            "target_file_name": f"{output_path}/{source_code}-{tg}{alpha_extension}.jsonl",
            "target_prefix": source_code,
            "target_cnt": 0,
            "target_lines": [],
        }
proc_status = "Complete"
proc_start_time = time.time()
for source_code, source_file in source_files.items():
    try:
        with open(source_file, "r", encoding="utf-8") as sourcef:
            print(f"\nProcessing {source_file}\n")

            source_cnt = 0
            rtype_skip_cnt = 0
            alpha_skip_cnt = 0
            for line in sourcef:
                source_cnt += 1
                if source_cnt % cli_args.output_frequency == 0:
                    elapsed_mins = round((time.time() - proc_start_time) / 60, 1)
                    print(f"\n{source_cnt:,} rows read from {source_file} after {elapsed_mins} minutes")
                    for geo, stats in target_stats[source_code].items():
                        print(f"\t{geo:<{MAX_GEO_LEN}} - {stats['target_cnt']:,} rows found")

                if cli_args.debug:
                    print(json.dumps(json.loads(line), indent=4))

                # Continue early if there are no address attributes in the line
                # if '"ADDR_' not in line: # oops, what about business_addr...
                if "ADDR_" not in line:
                    if cli_args.debug:
                        print("-> no address!")
                    continue

                record_type_list = []
                name_list = []
                addr_list = []
                for attr_data in json_parser.parse(line):
                    if attr_data["ATTRIBUTE"] == "RECORD_TYPE":
                        record_type_list.append(attr_data["ATTR_VALUE"])
                    elif attr_data["ATTRIBUTE"] == "NAME" and cli_args.alpha_filter:
                        name_data = attr_data.get("ATTR_JSON")
                        if len(name_data.get("NAME_ORG", "")) > 0:
                            name_list.append(name_data["NAME_ORG"].lower().strip())
                        elif len(name_data.get("NAME_FULL", "")) > 0:
                            name_list.append(name_data["NAME_FULL"].lower().strip())
                        elif len(name_data.get("NAME_LAST", "")) > 0:
                            name_list.append(name_data["NAME_LAST"].lower().strip())

                    elif attr_data["ATTRIBUTE"] == "ADDRESS":
                        addr_data = attr_data.get("ATTR_JSON")
                        addr_data["ADDR_FULL"] = f' {addr_data.get("ADDR_FULL", "").replace(",", " ").lower()} '
                        addr_data["HAS_ADDR_FULL"] = bool(addr_data["ADDR_FULL"].strip())
                        addr_data["ADDR_CITY"] = addr_data.get("ADDR_CITY", "").lower().strip()
                        addr_data["ADDR_STATE"] = addr_data.get("ADDR_STATE", "").lower().strip()
                        addr_data["ADDR_POSTAL_CODE"] = addr_data.get("ADDR_POSTAL_CODE", "").lower().strip()
                        addr_data["ADDR_COUNTRY"] = addr_data.get("ADDR_COUNTRY", "").lower().strip()
                        addr_list.append(addr_data)

                if not any(v in VALID_RECORD_TYPES for v in record_type_list):
                    if cli_args.debug:
                        print("-> invalid record_type!")
                    rtype_skip_cnt += 1
                    continue

                if cli_args.alpha_filter and not any(n.startswith(cli_args.alpha_filter) for n in name_list):
                    if cli_args.debug:
                        print("-> failed alpha check!")
                    alpha_skip_cnt += 1
                    continue

                for target_geo in target_geos:
                    addr_cnt = 0
                    for addr_data in addr_list:
                        addr_cnt += 1
                        passed = globals()[GEOS[target_geo]["function"]](target_geo, addr_data) and confirm_country(
                            target_geo, addr_data
                        )
                        if cli_args.debug:
                            func_name = GEOS[target_geo]["function"]
                            result = "PASSED" if passed else "FAILED"
                            print(f"testing addr {addr_cnt} for {target_geo.upper()} with {func_name}() {result}")
                        if passed:
                            target_stats[source_code][target_geo]["target_cnt"] += 1
                            target_stats[source_code][target_geo]["target_lines"].append(line)
                        elif cli_args.debug:
                            print("\tADDR_FULL", addr_data["ADDR_FULL"])
                            print("\tADDR_CITY", addr_data["ADDR_CITY"], "->", GEOS[target_geo].get("cities"))
                            print("\tADDR_STATE", addr_data["ADDR_STATE"], "->", GEOS[target_geo].get("states"))
                            print("\tADDR_COUNTRY", addr_data["ADDR_COUNTRY"], "->", GEOS[target_geo].get("countries"))

                if cli_args.debug:
                    input("\npress any key")

    except KeyboardInterrupt:
        proc_status = "Interrupted"
        print("Keyboard interrupt!")
        break
    except OSError as err:  # Exception as err:
        proc_status = "Errored out!"
        print(f"\nERROR: {err}", flush=True)
        break

print(f"\n\nProcessing {proc_status}")
print("-" * 19)
for f in source_files:
    print(f"\n{f} - {source_cnt:,} rows read")
    for geo, stats in target_stats[f].items():
        print(f"\t{geo:<{MAX_GEO_LEN}} - {stats['target_cnt']:,} rows found")
        output_filename = stats["target_file_name"]
        target_lines = stats["target_lines"]
        if len(target_lines) > 0:
            with open(output_filename, "w", encoding="utf-8") as targetf:
                # print(f"writing {output_filename} ...")
                targetf.writelines(target_lines)


if invalid_country_log:
    print("\nInvalid country log ...")
    print(json.dumps(invalid_country_log, indent=4))
    print()
