#!/usr/bin/env python3
"""
Seed aws_regions table in LocalStack DynamoDB.
Source: AWS official docs + coordinates from public gist (2026-05-09)

Usage:
    python scripts/seed_aws_regions.py
    python scripts/seed_aws_regions.py --endpoint http://localhost:4570
"""

from _local import LOCAL_CONFIG
import argparse
import boto3
from botocore.exceptions import ClientError
from decimal import Decimal

AWS_REGIONS = [
    # Americas
    {"region_id": "us-east-1",      "name": "US East (N. Virginia)",       "lat":  38.994,  "lon":  -77.452, "country_cca2": "US", "geography": "Americas",      "opt_in_required": False, "az_count": 6},
    {"region_id": "us-east-2",      "name": "US East (Ohio)",               "lat":  40.094,  "lon":  -82.754, "country_cca2": "US", "geography": "Americas",      "opt_in_required": False, "az_count": 3},
    {"region_id": "us-west-1",      "name": "US West (N. California)",      "lat":  37.444,  "lon": -122.154, "country_cca2": "US", "geography": "Americas",      "opt_in_required": False, "az_count": 3},
    {"region_id": "us-west-2",      "name": "US West (Oregon)",             "lat":  45.917,  "lon": -119.268, "country_cca2": "US", "geography": "Americas",      "opt_in_required": False, "az_count": 4},
    {"region_id": "ca-central-1",   "name": "Canada (Central)",             "lat":  45.500,  "lon":  -73.600, "country_cca2": "CA", "geography": "Americas",      "opt_in_required": False, "az_count": 3},
    {"region_id": "ca-west-1",      "name": "Canada West (Calgary)",        "lat":  51.045,  "lon": -114.072, "country_cca2": "CA", "geography": "Americas",      "opt_in_required": True,  "az_count": 3},
    {"region_id": "mx-central-1",   "name": "Mexico (Central)",             "lat":  19.433,  "lon":  -99.133, "country_cca2": "MX", "geography": "Americas",      "opt_in_required": True,  "az_count": 3},
    {"region_id": "sa-east-1",      "name": "South America (São Paulo)",    "lat": -23.493,  "lon":  -46.811, "country_cca2": "BR", "geography": "Americas",      "opt_in_required": False, "az_count": 3},

    # Europe
    {"region_id": "eu-west-1",      "name": "Europe (Ireland)",             "lat":  53.406,  "lon":   -6.225, "country_cca2": "IE", "geography": "Europe",        "opt_in_required": False, "az_count": 3},
    {"region_id": "eu-west-2",      "name": "Europe (London)",              "lat":  51.509,  "lon":   -0.061, "country_cca2": "GB", "geography": "Europe",        "opt_in_required": False, "az_count": 3},
    {"region_id": "eu-west-3",      "name": "Europe (Paris)",               "lat":  48.601,  "lon":    2.298, "country_cca2": "FR", "geography": "Europe",        "opt_in_required": False, "az_count": 3},
    {"region_id": "eu-central-1",   "name": "Europe (Frankfurt)",           "lat":  50.099,  "lon":    8.630, "country_cca2": "DE", "geography": "Europe",        "opt_in_required": False, "az_count": 3},
    {"region_id": "eu-central-2",   "name": "Europe (Zurich)",              "lat":  47.377,  "lon":    8.542, "country_cca2": "CH", "geography": "Europe",        "opt_in_required": True,  "az_count": 3},
    {"region_id": "eu-north-1",     "name": "Europe (Stockholm)",           "lat":  59.326,  "lon":   17.842, "country_cca2": "SE", "geography": "Europe",        "opt_in_required": False, "az_count": 3},
    {"region_id": "eu-south-1",     "name": "Europe (Milan)",               "lat":  45.463,  "lon":    9.108, "country_cca2": "IT", "geography": "Europe",        "opt_in_required": True,  "az_count": 3},
    {"region_id": "eu-south-2",     "name": "Europe (Spain)",               "lat":  40.417,  "lon":   -3.704, "country_cca2": "ES", "geography": "Europe",        "opt_in_required": True,  "az_count": 3},
    {"region_id": "il-central-1",   "name": "Israel (Tel Aviv)",            "lat":  32.085,  "lon":   34.782, "country_cca2": "IL", "geography": "Europe",        "opt_in_required": True,  "az_count": 3},

    # Asia Pacific
    {"region_id": "ap-northeast-1", "name": "Asia Pacific (Tokyo)",         "lat":  35.617,  "lon":  139.746, "country_cca2": "JP", "geography": "Asia Pacific",  "opt_in_required": False, "az_count": 4},
    {"region_id": "ap-northeast-2", "name": "Asia Pacific (Seoul)",         "lat":  37.562,  "lon":  126.874, "country_cca2": "KR", "geography": "Asia Pacific",  "opt_in_required": False, "az_count": 4},
    {"region_id": "ap-northeast-3", "name": "Asia Pacific (Osaka)",         "lat":  34.694,  "lon":  135.502, "country_cca2": "JP", "geography": "Asia Pacific",  "opt_in_required": False, "az_count": 3},
    {"region_id": "ap-southeast-1", "name": "Asia Pacific (Singapore)",     "lat":   1.322,  "lon":  103.693, "country_cca2": "SG", "geography": "Asia Pacific",  "opt_in_required": False, "az_count": 3},
    {"region_id": "ap-southeast-2", "name": "Asia Pacific (Sydney)",        "lat": -33.912,  "lon":  151.191, "country_cca2": "AU", "geography": "Asia Pacific",  "opt_in_required": False, "az_count": 3},
    {"region_id": "ap-southeast-3", "name": "Asia Pacific (Jakarta)",       "lat":  -6.209,  "lon":  106.846, "country_cca2": "ID", "geography": "Asia Pacific",  "opt_in_required": True,  "az_count": 3},
    {"region_id": "ap-southeast-4", "name": "Asia Pacific (Melbourne)",     "lat": -37.814,  "lon":  144.963, "country_cca2": "AU", "geography": "Asia Pacific",  "opt_in_required": True,  "az_count": 3},
    {"region_id": "ap-southeast-5", "name": "Asia Pacific (Malaysia)",      "lat":   3.139,  "lon":  101.687, "country_cca2": "MY", "geography": "Asia Pacific",  "opt_in_required": True,  "az_count": 3},
    {"region_id": "ap-southeast-6", "name": "Asia Pacific (New Zealand)",   "lat": -36.849,  "lon":  174.763, "country_cca2": "NZ", "geography": "Asia Pacific",  "opt_in_required": True,  "az_count": 3},
    {"region_id": "ap-southeast-7", "name": "Asia Pacific (Thailand)",      "lat":  13.756,  "lon":  100.502, "country_cca2": "TH", "geography": "Asia Pacific",  "opt_in_required": True,  "az_count": 3},
    {"region_id": "ap-south-1",     "name": "Asia Pacific (Mumbai)",        "lat":  19.243,  "lon":   72.967, "country_cca2": "IN", "geography": "Asia Pacific",  "opt_in_required": False, "az_count": 3},
    {"region_id": "ap-south-2",     "name": "Asia Pacific (Hyderabad)",     "lat":  17.385,  "lon":   78.487, "country_cca2": "IN", "geography": "Asia Pacific",  "opt_in_required": True,  "az_count": 3},
    {"region_id": "ap-east-1",      "name": "Asia Pacific (Hong Kong)",     "lat":  22.291,  "lon":  114.272, "country_cca2": "HK", "geography": "Asia Pacific",  "opt_in_required": True,  "az_count": 3},
    {"region_id": "ap-east-2",      "name": "Asia Pacific (Taipei)",        "lat":  25.033,  "lon":  121.565, "country_cca2": "TW", "geography": "Asia Pacific",  "opt_in_required": True,  "az_count": 3},

    # Middle East & Africa
    {"region_id": "me-south-1",     "name": "Middle East (Bahrain)",        "lat":  25.941,  "lon":   50.307, "country_cca2": "BH", "geography": "Middle East",   "opt_in_required": True,  "az_count": 3},
    {"region_id": "me-central-1",   "name": "Middle East (UAE)",            "lat":  25.205,  "lon":   55.271, "country_cca2": "AE", "geography": "Middle East",   "opt_in_required": True,  "az_count": 3},
    {"region_id": "af-south-1",     "name": "Africa (Cape Town)",           "lat": -33.915,  "lon":   18.376, "country_cca2": "ZA", "geography": "Africa",        "opt_in_required": True,  "az_count": 3},

    # China (separate partition)
    {"region_id": "cn-north-1",     "name": "China (Beijing)",              "lat":  39.809,  "lon":  116.578, "country_cca2": "CN", "geography": "China",         "opt_in_required": True,  "az_count": 3},
    {"region_id": "cn-northwest-1", "name": "China (Ningxia)",              "lat":  37.502,  "lon":  105.163, "country_cca2": "CN", "geography": "China",         "opt_in_required": True,  "az_count": 3},

    # GovCloud (US) — separate partition, US government use
    {"region_id": "us-gov-east-1",  "name": "AWS GovCloud (US-East)",       "lat":  38.900,  "lon":  -77.500, "country_cca2": "US", "geography": "GovCloud",      "opt_in_required": True,  "az_count": 3},
    {"region_id": "us-gov-west-1",  "name": "AWS GovCloud (US-West)",       "lat":  45.850,  "lon": -119.700, "country_cca2": "US", "geography": "GovCloud",      "opt_in_required": True,  "az_count": 3},
]

TABLE_NAME = "aws_regions"


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
    for r in AWS_REGIONS:
        client.put_item(
            TableName=TABLE_NAME,
            Item={
                "region_id":      {"S": r["region_id"]},
                "name":           {"S": r["name"]},
                "lat":            {"N": str(r["lat"])},
                "lon":            {"N": str(r["lon"])},
                "country_cca2":   {"S": r["country_cca2"]},
                "geography":      {"S": r["geography"]},
                "opt_in_required":{"BOOL": r["opt_in_required"]},
                "az_count":       {"N": str(r["az_count"])},
            },
        )
    print(f"Seeded {len(AWS_REGIONS)} AWS regions into {TABLE_NAME}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://localhost:4570")
    args = parser.parse_args()
    client = get_client(args.endpoint)
    ensure_table(client)
    seed(client)


if __name__ == "__main__":
    main()
