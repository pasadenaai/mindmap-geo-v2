#!/usr/bin/env python3
"""
Update geo_countries DynamoDB records with flag SVG paths for both aspect ratios.

Adds two attributes to each country record:
  flag_1x1  — relative path: assets/countries/flags/1x1/<file>
  flag_4x3  — relative path: assets/countries/flags/4x3/<file>

Matching is done on cca3 (ISO alpha-3) against the index.json `name` field.
Countries with no matching flag are reported but not errored.

Usage:
    python scripts/update_countries_flags.py
    python scripts/update_countries_flags.py --endpoint http://localhost:4570
    python scripts/update_countries_flags.py --dry-run
"""

from _local import LOCAL_CONFIG
import argparse
import json
import pathlib
import boto3
from botocore.exceptions import ClientError

REPO_ROOT   = pathlib.Path(__file__).parent.parent
FLAGS_ROOT  = REPO_ROOT / "assets" / "countries" / "flags"
INDEX_1X1   = FLAGS_ROOT / "1x1" / "index.json"
INDEX_4X3   = FLAGS_ROOT / "4x3" / "index.json"
TABLE_NAME  = "geo_countries"


def build_flag_map():
    """Return {cca3: {"flag_1x1": path, "flag_4x3": path}} from both indexes."""
    idx1 = json.loads(INDEX_1X1.read_text())
    idx4 = json.loads(INDEX_4X3.read_text())

    map1 = {entry["name"]: f"assets/countries/flags/1x1/{entry['file']}" for entry in idx1}
    map4 = {entry["name"]: f"assets/countries/flags/4x3/{entry['file']}" for entry in idx4}

    all_cca3 = set(map1) | set(map4)
    result = {}
    for cca3 in all_cca3:
        result[cca3] = {
            "flag_1x1": map1.get(cca3),
            "flag_4x3": map4.get(cca3),
        }
    return result


def get_all_countries(client):
    """Full scan of geo_countries — small table, single page."""
    items = []
    kwargs = {"TableName": TABLE_NAME}
    while True:
        resp = client.scan(**kwargs)
        items.extend(resp["Items"])
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://localhost:4570")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    args = parser.parse_args()

    flag_map = build_flag_map()

    client = boto3.client(
        "dynamodb",
        endpoint_url=args.endpoint,
        region_name="us-east-1",
        config=LOCAL_CONFIG,
    )

    countries = get_all_countries(client)
    updated = skipped = 0

    for item in countries:
        cca2 = item["cca2"]["S"]
        cca3 = item["cca3"]["S"]
        flags = flag_map.get(cca3)

        if not flags or (not flags["flag_1x1"] and not flags["flag_4x3"]):
            print(f"  NO FLAG  {cca2} / {cca3}")
            skipped += 1
            continue

        expr_parts = []
        expr_values = {}

        if flags["flag_1x1"]:
            expr_parts.append("flag_1x1 = :f1")
            expr_values[":f1"] = {"S": flags["flag_1x1"]}
        if flags["flag_4x3"]:
            expr_parts.append("flag_4x3 = :f4")
            expr_values[":f4"] = {"S": flags["flag_4x3"]}

        update_expr = "SET " + ", ".join(expr_parts)

        if args.dry_run:
            print(f"  DRY-RUN  {cca2} / {cca3}  →  {flags}")
        else:
            client.update_item(
                TableName=TABLE_NAME,
                Key={"cca2": {"S": cca2}},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values,
            )
        updated += 1

    action = "Would update" if args.dry_run else "Updated"
    print(f"\n{action} {updated} countries, skipped {skipped} (no matching flag).")


if __name__ == "__main__":
    main()
