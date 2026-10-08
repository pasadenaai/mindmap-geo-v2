#!/usr/bin/env python3
"""
Seed ibm_regions table in LocalStack DynamoDB.
Source: IBM Cloud docs — Multizone Regions (2026-05-09)

Usage:
    python scripts/seed_ibm_regions.py
    python scripts/seed_ibm_regions.py --endpoint http://localhost:4570
"""

from _local import LOCAL_CONFIG
import argparse
import boto3
from botocore.exceptions import ClientError

IBM_REGIONS = [
    # Americas
    {"region_id": "us-south",  "name": "US South (Dallas)",      "lat":  32.779,  "lon":  -96.809, "country_cca2": "US", "geography": "Americas",     "kind": "multizone"},
    {"region_id": "us-east",   "name": "US East (Washington DC)", "lat":  38.895,  "lon":  -77.036, "country_cca2": "US", "geography": "Americas",     "kind": "multizone"},
    {"region_id": "ca-tor",    "name": "Canada (Toronto)",        "lat":  43.651,  "lon":  -79.383, "country_cca2": "CA", "geography": "Americas",     "kind": "multizone"},
    {"region_id": "br-sao",    "name": "Brazil (São Paulo)",      "lat": -23.493,  "lon":  -46.811, "country_cca2": "BR", "geography": "Americas",     "kind": "multizone"},

    # Europe
    {"region_id": "eu-gb",     "name": "United Kingdom (London)", "lat":  51.509,  "lon":   -0.061, "country_cca2": "GB", "geography": "Europe",       "kind": "multizone"},
    {"region_id": "eu-de",     "name": "Germany (Frankfurt)",     "lat":  50.099,  "lon":    8.630, "country_cca2": "DE", "geography": "Europe",       "kind": "multizone"},
    {"region_id": "eu-es",     "name": "Spain (Madrid)",          "lat":  40.417,  "lon":   -3.704, "country_cca2": "ES", "geography": "Europe",       "kind": "multizone"},
    {"region_id": "eu-fr2",    "name": "France (Paris)",          "lat":  48.601,  "lon":    2.298, "country_cca2": "FR", "geography": "Europe",       "kind": "multizone"},

    # Asia Pacific
    {"region_id": "au-syd",    "name": "Australia (Sydney)",      "lat": -33.912,  "lon":  151.191, "country_cca2": "AU", "geography": "Asia Pacific", "kind": "multizone"},
    {"region_id": "jp-tok",    "name": "Japan (Tokyo)",           "lat":  35.617,  "lon":  139.746, "country_cca2": "JP", "geography": "Asia Pacific", "kind": "multizone"},
    {"region_id": "jp-osa",    "name": "Japan (Osaka)",           "lat":  34.694,  "lon":  135.502, "country_cca2": "JP", "geography": "Asia Pacific", "kind": "multizone"},
    {"region_id": "in-che",    "name": "India (Chennai)",         "lat":  13.082,  "lon":   80.270, "country_cca2": "IN", "geography": "Asia Pacific", "kind": "multizone"},
    {"region_id": "kr-seo",    "name": "Korea (Seoul)",           "lat":  37.562,  "lon":  126.874, "country_cca2": "KR", "geography": "Asia Pacific", "kind": "multizone"},
]

TABLE_NAME = "ibm_regions"


def get_client(endpoint):
    return boto3.client(
        "dynamodb",
        endpoint_url=endpoint,
        region_name="us-east-1",
        config=LOCAL_CONFIG,
    )


def ensure_table(client):
    try:
        client.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "region_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "region_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        client.get_waiter("table_exists").wait(TableName=TABLE_NAME)
        print(f"Created table {TABLE_NAME}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"Table {TABLE_NAME} already exists")
        else:
            raise


def seed(client):
    for r in IBM_REGIONS:
        client.put_item(
            TableName=TABLE_NAME,
            Item={
                "region_id":    {"S": r["region_id"]},
                "name":         {"S": r["name"]},
                "lat":          {"N": str(r["lat"])},
                "lon":          {"N": str(r["lon"])},
                "country_cca2": {"S": r["country_cca2"]},
                "geography":    {"S": r["geography"]},
                "kind":         {"S": r["kind"]},
            },
        )
    print(f"Seeded {len(IBM_REGIONS)} IBM Cloud regions into {TABLE_NAME}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://localhost:4570")
    args = parser.parse_args()
    client = get_client(args.endpoint)
    ensure_table(client)
    seed(client)


if __name__ == "__main__":
    main()
