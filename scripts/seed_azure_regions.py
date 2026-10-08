#!/usr/bin/env python3
"""
Seed azure_regions table in LocalStack DynamoDB.
Source: Microsoft Learn - List of Azure regions (updated 2026-03-23)
https://learn.microsoft.com/en-us/azure/reliability/regions-list

Usage:
    python scripts/seed_azure_regions.py
    python scripts/seed_azure_regions.py --endpoint http://localhost:4570
"""

from _local import LOCAL_CONFIG
import argparse
import boto3
from botocore.exceptions import ClientError

# restricted=True means access requires a request to Microsoft
AZURE_REGIONS = [
    # ── Americas ──────────────────────────────────────────────────────────────
    {"region_id": "eastus",           "name": "East US",               "physical_location": "Virginia",        "country_cca2": "US", "geography": "Americas",     "lat":  37.383,  "lon":  -78.820, "has_az": True,  "restricted": False},
    {"region_id": "eastus2",          "name": "East US 2",             "physical_location": "Virginia",        "country_cca2": "US", "geography": "Americas",     "lat":  36.665,  "lon":  -78.395, "has_az": True,  "restricted": False},
    {"region_id": "eastus3",          "name": "East US 3",             "physical_location": "Georgia",         "country_cca2": "US", "geography": "Americas",     "lat":  33.749,  "lon":  -84.388, "has_az": True,  "restricted": False},
    {"region_id": "centralus",        "name": "Central US",            "physical_location": "Iowa",            "country_cca2": "US", "geography": "Americas",     "lat":  41.878,  "lon":  -93.097, "has_az": True,  "restricted": False},
    {"region_id": "northcentralus",   "name": "North Central US",      "physical_location": "Illinois",        "country_cca2": "US", "geography": "Americas",     "lat":  41.850,  "lon":  -87.650, "has_az": False, "restricted": False},
    {"region_id": "southcentralus",   "name": "South Central US",      "physical_location": "Texas",           "country_cca2": "US", "geography": "Americas",     "lat":  29.425,  "lon":  -98.494, "has_az": True,  "restricted": False},
    {"region_id": "westcentralus",    "name": "West Central US",       "physical_location": "Wyoming",         "country_cca2": "US", "geography": "Americas",     "lat":  41.060,  "lon": -110.040, "has_az": False, "restricted": False},
    {"region_id": "westus",           "name": "West US",               "physical_location": "California",      "country_cca2": "US", "geography": "Americas",     "lat":  37.783,  "lon": -122.417, "has_az": False, "restricted": False},
    {"region_id": "westus2",          "name": "West US 2",             "physical_location": "Washington",      "country_cca2": "US", "geography": "Americas",     "lat":  47.233,  "lon": -119.852, "has_az": True,  "restricted": False},
    {"region_id": "westus3",          "name": "West US 3",             "physical_location": "Phoenix",         "country_cca2": "US", "geography": "Americas",     "lat":  33.448,  "lon": -112.074, "has_az": True,  "restricted": False},
    {"region_id": "canadacentral",    "name": "Canada Central",        "physical_location": "Toronto",         "country_cca2": "CA", "geography": "Americas",     "lat":  43.653,  "lon":  -79.383, "has_az": True,  "restricted": False},
    {"region_id": "canadaeast",       "name": "Canada East",           "physical_location": "Quebec",          "country_cca2": "CA", "geography": "Americas",     "lat":  46.817,  "lon":  -71.218, "has_az": False, "restricted": False},
    {"region_id": "brazilsouth",      "name": "Brazil South",          "physical_location": "Sao Paulo",       "country_cca2": "BR", "geography": "Americas",     "lat": -23.533,  "lon":  -46.626, "has_az": True,  "restricted": False},
    {"region_id": "brazilsoutheast",  "name": "Brazil Southeast",      "physical_location": "Rio de Janeiro",  "country_cca2": "BR", "geography": "Americas",     "lat": -22.908,  "lon":  -43.173, "has_az": False, "restricted": True},
    {"region_id": "mexicocentral",    "name": "Mexico Central",        "physical_location": "Querétaro",       "country_cca2": "MX", "geography": "Americas",     "lat":  20.587,  "lon": -100.390, "has_az": True,  "restricted": False},
    {"region_id": "chilecentral",     "name": "Chile Central",         "physical_location": "Santiago",        "country_cca2": "CL", "geography": "Americas",     "lat": -33.459,  "lon":  -70.648, "has_az": True,  "restricted": False},

    # ── Europe ────────────────────────────────────────────────────────────────
    {"region_id": "northeurope",      "name": "North Europe",          "physical_location": "Ireland",         "country_cca2": "IE", "geography": "Europe",       "lat":  53.350,  "lon":   -6.266, "has_az": True,  "restricted": False},
    {"region_id": "westeurope",       "name": "West Europe",           "physical_location": "Netherlands",     "country_cca2": "NL", "geography": "Europe",       "lat":  52.370,  "lon":    4.904, "has_az": True,  "restricted": False},
    {"region_id": "uksouth",          "name": "UK South",              "physical_location": "London",          "country_cca2": "GB", "geography": "Europe",       "lat":  51.509,  "lon":   -0.118, "has_az": True,  "restricted": False},
    {"region_id": "ukwest",           "name": "UK West",               "physical_location": "Cardiff",         "country_cca2": "GB", "geography": "Europe",       "lat":  51.484,  "lon":   -3.186, "has_az": False, "restricted": False},
    {"region_id": "francecentral",    "name": "France Central",        "physical_location": "Paris",           "country_cca2": "FR", "geography": "Europe",       "lat":  48.857,  "lon":    2.351, "has_az": True,  "restricted": False},
    {"region_id": "francesouth",      "name": "France South",          "physical_location": "Marseille",       "country_cca2": "FR", "geography": "Europe",       "lat":  43.297,  "lon":    5.381, "has_az": False, "restricted": True},
    {"region_id": "germanywestcentral","name": "Germany West Central", "physical_location": "Frankfurt",       "country_cca2": "DE", "geography": "Europe",       "lat":  50.110,  "lon":    8.682, "has_az": True,  "restricted": False},
    {"region_id": "germanynorth",     "name": "Germany North",         "physical_location": "Berlin",          "country_cca2": "DE", "geography": "Europe",       "lat":  52.520,  "lon":   13.405, "has_az": False, "restricted": True},
    {"region_id": "norwayeast",       "name": "Norway East",           "physical_location": "Norway",          "country_cca2": "NO", "geography": "Europe",       "lat":  59.913,  "lon":   10.752, "has_az": True,  "restricted": False},
    {"region_id": "norwaywest",       "name": "Norway West",           "physical_location": "Norway",          "country_cca2": "NO", "geography": "Europe",       "lat":  58.970,  "lon":    5.734, "has_az": False, "restricted": True},
    {"region_id": "swedencentral",    "name": "Sweden Central",        "physical_location": "Gävle",           "country_cca2": "SE", "geography": "Europe",       "lat":  60.674,  "lon":   17.142, "has_az": True,  "restricted": False},
    {"region_id": "switzerlandnorth", "name": "Switzerland North",     "physical_location": "Zurich",          "country_cca2": "CH", "geography": "Europe",       "lat":  47.377,  "lon":    8.542, "has_az": True,  "restricted": False},
    {"region_id": "switzerlandwest",  "name": "Switzerland West",      "physical_location": "Geneva",          "country_cca2": "CH", "geography": "Europe",       "lat":  46.204,  "lon":    6.143, "has_az": False, "restricted": True},
    {"region_id": "italynorth",       "name": "Italy North",           "physical_location": "Milan",           "country_cca2": "IT", "geography": "Europe",       "lat":  45.463,  "lon":    9.188, "has_az": True,  "restricted": False},
    {"region_id": "polandcentral",    "name": "Poland Central",        "physical_location": "Warsaw",          "country_cca2": "PL", "geography": "Europe",       "lat":  52.232,  "lon":   21.008, "has_az": True,  "restricted": False},
    {"region_id": "spaincentral",     "name": "Spain Central",         "physical_location": "Madrid",          "country_cca2": "ES", "geography": "Europe",       "lat":  40.417,  "lon":   -3.704, "has_az": True,  "restricted": False},
    {"region_id": "denmarkeast",      "name": "Denmark East",          "physical_location": "Copenhagen",      "country_cca2": "DK", "geography": "Europe",       "lat":  55.676,  "lon":   12.568, "has_az": True,  "restricted": False},
    {"region_id": "austriaeast",      "name": "Austria East",          "physical_location": "Vienna",          "country_cca2": "AT", "geography": "Europe",       "lat":  48.208,  "lon":   16.373, "has_az": True,  "restricted": False},
    {"region_id": "belgiumcentral",   "name": "Belgium Central",       "physical_location": "Brussels",        "country_cca2": "BE", "geography": "Europe",       "lat":  50.851,  "lon":    4.352, "has_az": True,  "restricted": False},

    # ── Middle East ───────────────────────────────────────────────────────────
    {"region_id": "uaenorth",         "name": "UAE North",             "physical_location": "Dubai",           "country_cca2": "AE", "geography": "Middle East",  "lat":  25.205,  "lon":   55.271, "has_az": True,  "restricted": False},
    {"region_id": "uaecentral",       "name": "UAE Central",           "physical_location": "Abu Dhabi",       "country_cca2": "AE", "geography": "Middle East",  "lat":  24.453,  "lon":   54.377, "has_az": False, "restricted": True},
    {"region_id": "israelcentral",    "name": "Israel Central",        "physical_location": "Israel",          "country_cca2": "IL", "geography": "Middle East",  "lat":  31.970,  "lon":   34.818, "has_az": True,  "restricted": False},
    {"region_id": "qatarcentral",     "name": "Qatar Central",         "physical_location": "Doha",            "country_cca2": "QA", "geography": "Middle East",  "lat":  25.286,  "lon":   51.533, "has_az": True,  "restricted": False},

    # ── Africa ────────────────────────────────────────────────────────────────
    {"region_id": "southafricanorth", "name": "South Africa North",   "physical_location": "Johannesburg",    "country_cca2": "ZA", "geography": "Africa",       "lat": -26.195,  "lon":   28.034, "has_az": True,  "restricted": False},
    {"region_id": "southafricawest",  "name": "South Africa West",    "physical_location": "Cape Town",       "country_cca2": "ZA", "geography": "Africa",       "lat": -33.925,  "lon":   18.424, "has_az": False, "restricted": True},

    # ── Asia Pacific ──────────────────────────────────────────────────────────
    {"region_id": "australiaeast",    "name": "Australia East",        "physical_location": "New South Wales", "country_cca2": "AU", "geography": "Asia Pacific", "lat": -33.868,  "lon":  151.207, "has_az": True,  "restricted": False},
    {"region_id": "australiasoutheast","name": "Australia Southeast",  "physical_location": "Victoria",        "country_cca2": "AU", "geography": "Asia Pacific", "lat": -37.814,  "lon":  144.963, "has_az": False, "restricted": False},
    {"region_id": "australiacentral", "name": "Australia Central",     "physical_location": "Canberra",        "country_cca2": "AU", "geography": "Asia Pacific", "lat": -35.281,  "lon":  149.129, "has_az": False, "restricted": False},
    {"region_id": "australiacentral2","name": "Australia Central 2",  "physical_location": "Canberra",        "country_cca2": "AU", "geography": "Asia Pacific", "lat": -35.310,  "lon":  149.100, "has_az": False, "restricted": True},
    {"region_id": "eastasia",         "name": "East Asia",             "physical_location": "Hong Kong",       "country_cca2": "HK", "geography": "Asia Pacific", "lat":  22.319,  "lon":  114.170, "has_az": True,  "restricted": False},
    {"region_id": "southeastasia",    "name": "Southeast Asia",        "physical_location": "Singapore",       "country_cca2": "SG", "geography": "Asia Pacific", "lat":   1.352,  "lon":  103.820, "has_az": True,  "restricted": False},
    {"region_id": "japaneast",        "name": "Japan East",            "physical_location": "Tokyo",           "country_cca2": "JP", "geography": "Asia Pacific", "lat":  35.682,  "lon":  139.759, "has_az": True,  "restricted": False},
    {"region_id": "japanwest",        "name": "Japan West",            "physical_location": "Osaka",           "country_cca2": "JP", "geography": "Asia Pacific", "lat":  34.694,  "lon":  135.502, "has_az": True,  "restricted": False},
    {"region_id": "koreacentral",     "name": "Korea Central",         "physical_location": "Seoul",           "country_cca2": "KR", "geography": "Asia Pacific", "lat":  37.563,  "lon":  126.997, "has_az": True,  "restricted": False},
    {"region_id": "koreasouth",       "name": "Korea South",           "physical_location": "Busan",           "country_cca2": "KR", "geography": "Asia Pacific", "lat":  35.180,  "lon":  129.075, "has_az": False, "restricted": False},
    {"region_id": "centralindia",     "name": "Central India",         "physical_location": "Pune",            "country_cca2": "IN", "geography": "Asia Pacific", "lat":  18.520,  "lon":   73.856, "has_az": True,  "restricted": False},
    {"region_id": "southindia",       "name": "South India",           "physical_location": "Chennai",         "country_cca2": "IN", "geography": "Asia Pacific", "lat":  13.083,  "lon":   80.270, "has_az": False, "restricted": False},
    {"region_id": "westindia",        "name": "West India",            "physical_location": "Mumbai",          "country_cca2": "IN", "geography": "Asia Pacific", "lat":  19.076,  "lon":   72.878, "has_az": False, "restricted": False},
    {"region_id": "indonesiacentral", "name": "Indonesia Central",     "physical_location": "Jakarta",         "country_cca2": "ID", "geography": "Asia Pacific", "lat":  -6.209,  "lon":  106.846, "has_az": True,  "restricted": False},
    {"region_id": "malaysiawest",     "name": "Malaysia West",         "physical_location": "Kuala Lumpur",   "country_cca2": "MY", "geography": "Asia Pacific", "lat":   3.139,  "lon":  101.687, "has_az": True,  "restricted": False},
    {"region_id": "newzealandnorth",  "name": "New Zealand North",     "physical_location": "Auckland",        "country_cca2": "NZ", "geography": "Asia Pacific", "lat": -36.849,  "lon":  174.763, "has_az": True,  "restricted": False},
]

TABLE_NAME = "azure_regions"


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
    for r in AZURE_REGIONS:
        client.put_item(
            TableName=TABLE_NAME,
            Item={
                "region_id":          {"S": r["region_id"]},
                "name":               {"S": r["name"]},
                "physical_location":  {"S": r["physical_location"]},
                "country_cca2":       {"S": r["country_cca2"]},
                "geography":          {"S": r["geography"]},
                "lat":                {"N": str(r["lat"])},
                "lon":                {"N": str(r["lon"])},
                "has_az":             {"BOOL": r["has_az"]},
                "restricted":         {"BOOL": r["restricted"]},
            },
        )
    print(f"Seeded {len(AZURE_REGIONS)} Azure regions into {TABLE_NAME}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://localhost:4570")
    args = parser.parse_args()
    client = get_client(args.endpoint)
    ensure_table(client)
    seed(client)


if __name__ == "__main__":
    main()
