#!/usr/bin/env python3
"""
Seed gcp_regions table in LocalStack DynamoDB.
Source: Google Cloud official docs (2026-05-09)

Usage:
    python scripts/seed_gcp_regions.py
    python scripts/seed_gcp_regions.py --endpoint http://localhost:4570
"""

from _local import LOCAL_CONFIG
import argparse
import boto3
from botocore.exceptions import ClientError

GCP_REGIONS = [
    # Americas
    {"region_id": "us-central1",              "name": "Iowa",                     "lat":  41.878,  "lon":  -93.098, "country_cca2": "US", "geography": "Americas",      "zone_count": 4},
    {"region_id": "us-east1",                 "name": "South Carolina",           "lat":  33.196,  "lon":  -80.013, "country_cca2": "US", "geography": "Americas",      "zone_count": 4},
    {"region_id": "us-east4",                 "name": "N. Virginia",              "lat":  38.853,  "lon":  -77.305, "country_cca2": "US", "geography": "Americas",      "zone_count": 3},
    {"region_id": "us-east5",                 "name": "Columbus",                 "lat":  39.961,  "lon":  -82.999, "country_cca2": "US", "geography": "Americas",      "zone_count": 3},
    {"region_id": "us-south1",               "name": "Dallas",                   "lat":  32.779,  "lon":  -96.809, "country_cca2": "US", "geography": "Americas",      "zone_count": 3},
    {"region_id": "us-west1",                 "name": "Oregon",                   "lat":  45.600,  "lon": -121.184, "country_cca2": "US", "geography": "Americas",      "zone_count": 4},
    {"region_id": "us-west2",                 "name": "Los Angeles",              "lat":  34.052,  "lon": -118.244, "country_cca2": "US", "geography": "Americas",      "zone_count": 3},
    {"region_id": "us-west3",                 "name": "Salt Lake City",           "lat":  40.758,  "lon": -111.888, "country_cca2": "US", "geography": "Americas",      "zone_count": 3},
    {"region_id": "us-west4",                 "name": "Las Vegas",                "lat":  36.175,  "lon": -115.137, "country_cca2": "US", "geography": "Americas",      "zone_count": 3},
    {"region_id": "northamerica-northeast1",  "name": "Montréal",                 "lat":  45.504,  "lon":  -73.574, "country_cca2": "CA", "geography": "Americas",      "zone_count": 3},
    {"region_id": "northamerica-northeast2",  "name": "Toronto",                  "lat":  43.651,  "lon":  -79.383, "country_cca2": "CA", "geography": "Americas",      "zone_count": 3},
    {"region_id": "southamerica-east1",       "name": "São Paulo",                "lat": -23.493,  "lon":  -46.811, "country_cca2": "BR", "geography": "Americas",      "zone_count": 3},
    {"region_id": "southamerica-west1",       "name": "Santiago",                 "lat": -33.459,  "lon":  -70.648, "country_cca2": "CL", "geography": "Americas",      "zone_count": 3},

    # Europe
    {"region_id": "europe-west1",             "name": "Belgium",                  "lat":  50.448,  "lon":    3.819, "country_cca2": "BE", "geography": "Europe",        "zone_count": 4},
    {"region_id": "europe-west2",             "name": "London",                   "lat":  51.509,  "lon":   -0.061, "country_cca2": "GB", "geography": "Europe",        "zone_count": 3},
    {"region_id": "europe-west3",             "name": "Frankfurt",                "lat":  50.099,  "lon":    8.630, "country_cca2": "DE", "geography": "Europe",        "zone_count": 3},
    {"region_id": "europe-west4",             "name": "Netherlands",              "lat":  53.430,  "lon":    6.870, "country_cca2": "NL", "geography": "Europe",        "zone_count": 3},
    {"region_id": "europe-west6",             "name": "Zürich",                   "lat":  47.377,  "lon":    8.542, "country_cca2": "CH", "geography": "Europe",        "zone_count": 3},
    {"region_id": "europe-west8",             "name": "Milan",                    "lat":  45.463,  "lon":    9.108, "country_cca2": "IT", "geography": "Europe",        "zone_count": 3},
    {"region_id": "europe-west9",             "name": "Paris",                    "lat":  48.601,  "lon":    2.298, "country_cca2": "FR", "geography": "Europe",        "zone_count": 3},
    {"region_id": "europe-west10",            "name": "Berlin",                   "lat":  52.520,  "lon":   13.405, "country_cca2": "DE", "geography": "Europe",        "zone_count": 3},
    {"region_id": "europe-west12",            "name": "Turin",                    "lat":  45.070,  "lon":    7.687, "country_cca2": "IT", "geography": "Europe",        "zone_count": 3},
    {"region_id": "europe-north1",            "name": "Finland",                  "lat":  60.569,  "lon":   27.188, "country_cca2": "FI", "geography": "Europe",        "zone_count": 3},
    {"region_id": "europe-central2",          "name": "Warsaw",                   "lat":  52.230,  "lon":   21.012, "country_cca2": "PL", "geography": "Europe",        "zone_count": 3},
    {"region_id": "europe-southwest1",        "name": "Madrid",                   "lat":  40.417,  "lon":   -3.704, "country_cca2": "ES", "geography": "Europe",        "zone_count": 3},

    # Middle East
    {"region_id": "me-west1",                 "name": "Tel Aviv",                 "lat":  32.085,  "lon":   34.782, "country_cca2": "IL", "geography": "Middle East",   "zone_count": 3},
    {"region_id": "me-central1",              "name": "Doha",                     "lat":  25.286,  "lon":   51.531, "country_cca2": "QA", "geography": "Middle East",   "zone_count": 3},
    {"region_id": "me-central2",              "name": "Dammam",                   "lat":  26.420,  "lon":   50.088, "country_cca2": "SA", "geography": "Middle East",   "zone_count": 3},

    # Africa
    {"region_id": "africa-south1",            "name": "Johannesburg",             "lat": -26.195,  "lon":   28.034, "country_cca2": "ZA", "geography": "Africa",        "zone_count": 3},

    # Asia Pacific
    {"region_id": "asia-east1",               "name": "Taiwan",                   "lat":  24.048,  "lon":  120.516, "country_cca2": "TW", "geography": "Asia Pacific",  "zone_count": 3},
    {"region_id": "asia-east2",               "name": "Hong Kong",                "lat":  22.291,  "lon":  114.272, "country_cca2": "HK", "geography": "Asia Pacific",  "zone_count": 3},
    {"region_id": "asia-northeast1",          "name": "Tokyo",                    "lat":  35.617,  "lon":  139.746, "country_cca2": "JP", "geography": "Asia Pacific",  "zone_count": 3},
    {"region_id": "asia-northeast2",          "name": "Osaka",                    "lat":  34.694,  "lon":  135.502, "country_cca2": "JP", "geography": "Asia Pacific",  "zone_count": 3},
    {"region_id": "asia-northeast3",          "name": "Seoul",                    "lat":  37.562,  "lon":  126.874, "country_cca2": "KR", "geography": "Asia Pacific",  "zone_count": 3},
    {"region_id": "asia-south1",              "name": "Mumbai",                   "lat":  19.243,  "lon":   72.967, "country_cca2": "IN", "geography": "Asia Pacific",  "zone_count": 3},
    {"region_id": "asia-south2",              "name": "Delhi",                    "lat":  28.614,  "lon":   77.209, "country_cca2": "IN", "geography": "Asia Pacific",  "zone_count": 3},
    {"region_id": "asia-southeast1",          "name": "Singapore",                "lat":   1.322,  "lon":  103.693, "country_cca2": "SG", "geography": "Asia Pacific",  "zone_count": 3},
    {"region_id": "asia-southeast2",          "name": "Jakarta",                  "lat":  -6.209,  "lon":  106.846, "country_cca2": "ID", "geography": "Asia Pacific",  "zone_count": 3},
    {"region_id": "australia-southeast1",     "name": "Sydney",                   "lat": -33.912,  "lon":  151.191, "country_cca2": "AU", "geography": "Asia Pacific",  "zone_count": 3},
    {"region_id": "australia-southeast2",     "name": "Melbourne",                "lat": -37.814,  "lon":  144.963, "country_cca2": "AU", "geography": "Asia Pacific",  "zone_count": 3},
]

TABLE_NAME = "gcp_regions"


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
    for r in GCP_REGIONS:
        client.put_item(
            TableName=TABLE_NAME,
            Item={
                "region_id":   {"S": r["region_id"]},
                "name":        {"S": r["name"]},
                "lat":         {"N": str(r["lat"])},
                "lon":         {"N": str(r["lon"])},
                "country_cca2":{"S": r["country_cca2"]},
                "geography":   {"S": r["geography"]},
                "zone_count":  {"N": str(r["zone_count"])},
            },
        )
    print(f"Seeded {len(GCP_REGIONS)} GCP regions into {TABLE_NAME}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://localhost:4570")
    args = parser.parse_args()
    client = get_client(args.endpoint)
    ensure_table(client)
    seed(client)


if __name__ == "__main__":
    main()
