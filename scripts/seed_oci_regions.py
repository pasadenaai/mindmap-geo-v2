#!/usr/bin/env python3
"""
Seed oci_regions table in LocalStack DynamoDB.
Source: Oracle Cloud Infrastructure docs (2026-05-09)

Usage:
    python scripts/seed_oci_regions.py
    python scripts/seed_oci_regions.py --endpoint http://localhost:4570
"""

from _local import LOCAL_CONFIG
import argparse
import boto3
from botocore.exceptions import ClientError

OCI_REGIONS = [
    # North America
    {"region_id": "us-ashburn-1",    "name": "US East (Ashburn)",          "lat":  38.853, "lon":  -77.305, "country_cca2": "US", "geography": "North America",  "realm": "commercial"},
    {"region_id": "us-phoenix-1",    "name": "US West (Phoenix)",           "lat":  33.448, "lon": -112.074, "country_cca2": "US", "geography": "North America",  "realm": "commercial"},
    {"region_id": "us-sanjose-1",    "name": "US West (San Jose)",          "lat":  37.338, "lon": -121.886, "country_cca2": "US", "geography": "North America",  "realm": "commercial"},
    {"region_id": "us-chicago-1",    "name": "US Midwest (Chicago)",        "lat":  41.878, "lon":  -87.630, "country_cca2": "US", "geography": "North America",  "realm": "commercial"},
    {"region_id": "us-saltlake-2",   "name": "US West (Salt Lake City)",    "lat":  40.758, "lon": -111.888, "country_cca2": "US", "geography": "North America",  "realm": "commercial"},
    {"region_id": "ca-toronto-1",    "name": "Canada Southeast (Toronto)",  "lat":  43.651, "lon":  -79.383, "country_cca2": "CA", "geography": "North America",  "realm": "commercial"},
    {"region_id": "ca-montreal-1",   "name": "Canada East (Montreal)",      "lat":  45.504, "lon":  -73.574, "country_cca2": "CA", "geography": "North America",  "realm": "commercial"},
    {"region_id": "mx-queretaro-1",  "name": "Mexico Central (Querétaro)",  "lat":  20.588, "lon": -100.389, "country_cca2": "MX", "geography": "North America",  "realm": "commercial"},
    {"region_id": "mx-monterrey-1",  "name": "Mexico Northeast (Monterrey)","lat":  25.686, "lon": -100.316, "country_cca2": "MX", "geography": "North America",  "realm": "commercial"},

    # Latin America
    {"region_id": "sa-saopaulo-1",   "name": "Brazil East (São Paulo)",     "lat": -23.493, "lon":  -46.811, "country_cca2": "BR", "geography": "Latin America",  "realm": "commercial"},
    {"region_id": "sa-vinhedo-1",    "name": "Brazil Southeast (Vinhedo)",  "lat": -23.028, "lon":  -47.032, "country_cca2": "BR", "geography": "Latin America",  "realm": "commercial"},
    {"region_id": "sa-bogota-1",     "name": "Colombia Central (Bogotá)",   "lat":   4.711, "lon":  -74.073, "country_cca2": "CO", "geography": "Latin America",  "realm": "commercial"},
    {"region_id": "sa-santiago-1",   "name": "Chile Central (Santiago)",    "lat": -33.459, "lon":  -70.648, "country_cca2": "CL", "geography": "Latin America",  "realm": "commercial"},

    # Europe
    {"region_id": "eu-frankfurt-1",  "name": "Germany Central (Frankfurt)", "lat":  50.099, "lon":    8.630, "country_cca2": "DE", "geography": "Europe",         "realm": "commercial"},
    {"region_id": "eu-amsterdam-1",  "name": "Netherlands Northwest (Amsterdam)", "lat": 52.370, "lon": 4.895, "country_cca2": "NL", "geography": "Europe",       "realm": "commercial"},
    {"region_id": "eu-milan-1",      "name": "Italy Northwest (Milan)",     "lat":  45.463, "lon":    9.108, "country_cca2": "IT", "geography": "Europe",         "realm": "commercial"},
    {"region_id": "eu-paris-1",      "name": "France Central (Paris)",      "lat":  48.601, "lon":    2.298, "country_cca2": "FR", "geography": "Europe",         "realm": "commercial"},
    {"region_id": "eu-madrid-1",     "name": "Spain Central (Madrid)",      "lat":  40.417, "lon":   -3.704, "country_cca2": "ES", "geography": "Europe",         "realm": "commercial"},
    {"region_id": "eu-stockholm-1",  "name": "Sweden Central (Stockholm)",  "lat":  59.326, "lon":   17.842, "country_cca2": "SE", "geography": "Europe",         "realm": "commercial"},
    {"region_id": "eu-zurich-1",     "name": "Switzerland North (Zürich)",  "lat":  47.377, "lon":    8.542, "country_cca2": "CH", "geography": "Europe",         "realm": "commercial"},
    {"region_id": "uk-london-1",     "name": "UK South (London)",           "lat":  51.509, "lon":   -0.061, "country_cca2": "GB", "geography": "Europe",         "realm": "commercial"},
    {"region_id": "uk-cardiff-1",    "name": "UK West (Newport)",           "lat":  51.584, "lon":   -2.998, "country_cca2": "GB", "geography": "Europe",         "realm": "commercial"},

    # Middle East
    {"region_id": "me-dubai-1",      "name": "UAE East (Dubai)",            "lat":  25.205, "lon":   55.271, "country_cca2": "AE", "geography": "Middle East",    "realm": "commercial"},
    {"region_id": "me-abudhabi-1",   "name": "UAE Central (Abu Dhabi)",     "lat":  24.453, "lon":   54.377, "country_cca2": "AE", "geography": "Middle East",    "realm": "commercial"},
    {"region_id": "me-riyadh-1",     "name": "Saudi Arabia West (Riyadh)",  "lat":  24.689, "lon":   46.672, "country_cca2": "SA", "geography": "Middle East",    "realm": "commercial"},
    {"region_id": "me-jeddah-1",     "name": "Saudi Arabia North (Jeddah)", "lat":  21.540, "lon":   39.173, "country_cca2": "SA", "geography": "Middle East",    "realm": "commercial"},
    {"region_id": "il-jerusalem-1",  "name": "Israel Central (Jerusalem)",  "lat":  31.769, "lon":   35.217, "country_cca2": "IL", "geography": "Middle East",    "realm": "commercial"},

    # Africa
    {"region_id": "af-johannesburg-1","name": "South Africa Central (Johannesburg)", "lat": -26.195, "lon": 28.034, "country_cca2": "ZA", "geography": "Africa", "realm": "commercial"},

    # Asia Pacific
    {"region_id": "ap-tokyo-1",      "name": "Japan East (Tokyo)",          "lat":  35.617, "lon":  139.746, "country_cca2": "JP", "geography": "Asia Pacific",   "realm": "commercial"},
    {"region_id": "ap-osaka-1",      "name": "Japan West (Osaka)",          "lat":  34.694, "lon":  135.502, "country_cca2": "JP", "geography": "Asia Pacific",   "realm": "commercial"},
    {"region_id": "ap-sydney-1",     "name": "Australia East (Sydney)",     "lat": -33.912, "lon":  151.191, "country_cca2": "AU", "geography": "Asia Pacific",   "realm": "commercial"},
    {"region_id": "ap-melbourne-1",  "name": "Australia Southeast (Melbourne)", "lat": -37.814, "lon": 144.963, "country_cca2": "AU", "geography": "Asia Pacific","realm": "commercial"},
    {"region_id": "ap-mumbai-1",     "name": "India West (Mumbai)",         "lat":  19.243, "lon":   72.967, "country_cca2": "IN", "geography": "Asia Pacific",   "realm": "commercial"},
    {"region_id": "ap-hyderabad-1",  "name": "India South (Hyderabad)",     "lat":  17.385, "lon":   78.487, "country_cca2": "IN", "geography": "Asia Pacific",   "realm": "commercial"},
    {"region_id": "ap-seoul-1",      "name": "South Korea Central (Seoul)", "lat":  37.562, "lon":  126.874, "country_cca2": "KR", "geography": "Asia Pacific",   "realm": "commercial"},
    {"region_id": "ap-chuncheon-1",  "name": "South Korea North (Chuncheon)","lat": 37.881, "lon":  127.730, "country_cca2": "KR", "geography": "Asia Pacific",   "realm": "commercial"},
    {"region_id": "ap-singapore-1",  "name": "Singapore (Singapore)",       "lat":   1.322, "lon":  103.693, "country_cca2": "SG", "geography": "Asia Pacific",   "realm": "commercial"},
    {"region_id": "ap-singapore-2",  "name": "Singapore West (Singapore)",  "lat":   1.290, "lon":  103.800, "country_cca2": "SG", "geography": "Asia Pacific",   "realm": "commercial"},
    {"region_id": "ap-jakarta-1",    "name": "Indonesia (Jakarta)",         "lat":  -6.209, "lon":  106.846, "country_cca2": "ID", "geography": "Asia Pacific",   "realm": "commercial"},
    {"region_id": "ap-malaysia-1",   "name": "Malaysia West (Kuala Lumpur)","lat":   3.139, "lon":  101.687, "country_cca2": "MY", "geography": "Asia Pacific",   "realm": "commercial"},
    {"region_id": "ap-malaysia-2",   "name": "Malaysia South (Johor)",      "lat":   1.493, "lon":  103.741, "country_cca2": "MY", "geography": "Asia Pacific",   "realm": "commercial"},
    {"region_id": "ap-taipei-1",     "name": "Taiwan (Taipei)",             "lat":  25.033, "lon":  121.565, "country_cca2": "TW", "geography": "Asia Pacific",   "realm": "commercial"},
    {"region_id": "ap-bangkok-1",    "name": "Thailand (Bangkok)",          "lat":  13.756, "lon":  100.502, "country_cca2": "TH", "geography": "Asia Pacific",   "realm": "commercial"},

    # Government
    {"region_id": "us-langley-1",    "name": "US Gov East (Ashburn)",       "lat":  38.900, "lon":  -77.460, "country_cca2": "US", "geography": "Government",     "realm": "government"},
    {"region_id": "us-luke-1",       "name": "US Gov West (Phoenix)",       "lat":  33.535, "lon": -112.371, "country_cca2": "US", "geography": "Government",     "realm": "government"},
]

TABLE_NAME = "oci_regions"


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
    for r in OCI_REGIONS:
        client.put_item(
            TableName=TABLE_NAME,
            Item={
                "region_id":    {"S": r["region_id"]},
                "name":         {"S": r["name"]},
                "lat":          {"N": str(r["lat"])},
                "lon":          {"N": str(r["lon"])},
                "country_cca2": {"S": r["country_cca2"]},
                "geography":    {"S": r["geography"]},
                "realm":        {"S": r["realm"]},
            },
        )
    print(f"Seeded {len(OCI_REGIONS)} OCI regions into {TABLE_NAME}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://localhost:4570")
    args = parser.parse_args()
    client = get_client(args.endpoint)
    ensure_table(client)
    seed(client)


if __name__ == "__main__":
    main()
