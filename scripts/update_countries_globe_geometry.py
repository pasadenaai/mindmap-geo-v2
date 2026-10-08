#!/usr/bin/env python3
"""
Update geo_countries DynamoDB records with globe geometry association flags.

Adds to every record:
  has_globe_geometry  (BOOL)  — true if the country appears in countries-110m.json
  globe_feature_id    (S)     — the TopoJSON feature id (= ccn3) for the 174 that do;
                                absent on records with no geometry

The join key is: TopoJSON feature.id (string) === DynamoDB ccn3 (string)

Three TopoJSON features carry no id (N. Cyprus, Somaliland, Kosovo — unrecognized
states). Kosovo is in the DB as XK/UNK but its TopoJSON feature has no numeric id,
so it is marked has_globe_geometry=false.

Usage:
    python scripts/update_countries_globe_geometry.py
    python scripts/update_countries_globe_geometry.py --endpoint http://localhost:4570
    python scripts/update_countries_globe_geometry.py --dry-run
"""

from _local import LOCAL_CONFIG
import argparse
import json
import pathlib
import boto3

REPO_ROOT  = pathlib.Path(__file__).parent.parent
TOPO_FILE  = REPO_ROOT / "frontend" / "public" / "data" / "countries-110m.json"
TABLE_NAME = "geo_countries"


def load_topo_ids():
    topo  = json.loads(TOPO_FILE.read_text())
    geoms = topo["objects"]["countries"]["geometries"]
    return {str(g["id"]) for g in geoms if "id" in g}


def get_all_countries(client):
    items, kwargs = [], {"TableName": TABLE_NAME}
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
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    topo_ids = load_topo_ids()
    print(f"TopoJSON feature IDs loaded: {len(topo_ids)}")

    client = boto3.client(
        "dynamodb",
        endpoint_url=args.endpoint,
        region_name="us-east-1",
        config=LOCAL_CONFIG,
    )

    countries = get_all_countries(client)
    matched = unmatched = 0

    for item in countries:
        cca2 = item["cca2"]["S"]
        ccn3 = item.get("ccn3", {}).get("S", "")
        has_geom = ccn3 in topo_ids

        if has_geom:
            update_expr  = "SET has_globe_geometry = :t, globe_feature_id = :fid"
            expr_values  = {
                ":t":   {"BOOL": True},
                ":fid": {"S": ccn3},
            }
            matched += 1
        else:
            # Remove globe_feature_id if it somehow exists, set flag false
            update_expr = "SET has_globe_geometry = :f REMOVE globe_feature_id"
            expr_values = {":f": {"BOOL": False}}
            unmatched += 1

        if args.dry_run:
            label = "MATCH  " if has_geom else "no-geom"
            print(f"  {label}  {cca2}/{ccn3 or '—'}")
        else:
            client.update_item(
                TableName=TABLE_NAME,
                Key={"cca2": {"S": cca2}},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values,
            )

    action = "Would set" if args.dry_run else "Set"
    print(f"\n{action} has_globe_geometry=true  on {matched} countries")
    print(f"{action} has_globe_geometry=false on {unmatched} countries")


if __name__ == "__main__":
    main()
