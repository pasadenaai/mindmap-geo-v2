#!/usr/bin/env python3
"""
Seed alibaba_regions table in LocalStack DynamoDB.
Source: Alibaba Cloud official docs (2026-05-09)

Usage:
    python scripts/seed_alibaba_regions.py
    python scripts/seed_alibaba_regions.py --endpoint http://localhost:4570
"""

from _local import LOCAL_CONFIG
import argparse
import boto3
from botocore.exceptions import ClientError

ALIBABA_REGIONS = [
    # China
    {"region_id": "cn-hangzhou",      "name": "China (Hangzhou)",          "lat":  30.274,  "lon":  120.155, "country_cca2": "CN", "geography": "China",        "china_region": True},
    {"region_id": "cn-shanghai",      "name": "China (Shanghai)",          "lat":  31.230,  "lon":  121.473, "country_cca2": "CN", "geography": "China",        "china_region": True},
    {"region_id": "cn-nanjing",       "name": "China (Nanjing)",           "lat":  32.061,  "lon":  118.796, "country_cca2": "CN", "geography": "China",        "china_region": True},
    {"region_id": "cn-fuzhou",        "name": "China (Fuzhou)",            "lat":  26.075,  "lon":  119.296, "country_cca2": "CN", "geography": "China",        "china_region": True},
    {"region_id": "cn-wuhan",         "name": "China (Wuhan)",             "lat":  30.593,  "lon":  114.305, "country_cca2": "CN", "geography": "China",        "china_region": True},
    {"region_id": "cn-qingdao",       "name": "China (Qingdao)",           "lat":  36.067,  "lon":  120.383, "country_cca2": "CN", "geography": "China",        "china_region": True},
    {"region_id": "cn-beijing",       "name": "China (Beijing)",           "lat":  39.909,  "lon":  116.397, "country_cca2": "CN", "geography": "China",        "china_region": True},
    {"region_id": "cn-zhangjiakou",   "name": "China (Zhangjiakou)",       "lat":  40.811,  "lon":  114.888, "country_cca2": "CN", "geography": "China",        "china_region": True},
    {"region_id": "cn-huhehaote",     "name": "China (Hohhot)",            "lat":  40.842,  "lon":  111.749, "country_cca2": "CN", "geography": "China",        "china_region": True},
    {"region_id": "cn-wulanchabu",    "name": "China (Ulanqab)",           "lat":  41.034,  "lon":  113.114, "country_cca2": "CN", "geography": "China",        "china_region": True},
    {"region_id": "cn-shenzhen",      "name": "China (Shenzhen)",          "lat":  22.543,  "lon":  114.058, "country_cca2": "CN", "geography": "China",        "china_region": True},
    {"region_id": "cn-heyuan",        "name": "China (Heyuan)",            "lat":  23.729,  "lon":  114.699, "country_cca2": "CN", "geography": "China",        "china_region": True},
    {"region_id": "cn-guangzhou",     "name": "China (Guangzhou)",         "lat":  23.129,  "lon":  113.264, "country_cca2": "CN", "geography": "China",        "china_region": True},
    {"region_id": "cn-chengdu",       "name": "China (Chengdu)",           "lat":  30.572,  "lon":  104.066, "country_cca2": "CN", "geography": "China",        "china_region": True},
    {"region_id": "cn-chongqing",     "name": "China (Chongqing)",         "lat":  29.563,  "lon":  106.551, "country_cca2": "CN", "geography": "China",        "china_region": True},
    {"region_id": "cn-zhengzhou",     "name": "China (Zhengzhou)",         "lat":  34.757,  "lon":  113.665, "country_cca2": "CN", "geography": "China",        "china_region": True},
    {"region_id": "cn-hongkong",      "name": "China (Hong Kong)",         "lat":  22.291,  "lon":  114.272, "country_cca2": "HK", "geography": "Asia Pacific", "china_region": False},

    # Asia Pacific
    {"region_id": "ap-southeast-1",   "name": "Asia Pacific SE 1 (Singapore)",   "lat":   1.322,  "lon":  103.693, "country_cca2": "SG", "geography": "Asia Pacific", "china_region": False},
    {"region_id": "ap-southeast-2",   "name": "Asia Pacific SE 2 (Sydney)",      "lat": -33.912,  "lon":  151.191, "country_cca2": "AU", "geography": "Asia Pacific", "china_region": False},
    {"region_id": "ap-southeast-3",   "name": "Asia Pacific SE 3 (Kuala Lumpur)","lat":   3.139,  "lon":  101.687, "country_cca2": "MY", "geography": "Asia Pacific", "china_region": False},
    {"region_id": "ap-southeast-5",   "name": "Asia Pacific SE 5 (Jakarta)",     "lat":  -6.209,  "lon":  106.846, "country_cca2": "ID", "geography": "Asia Pacific", "china_region": False},
    {"region_id": "ap-southeast-6",   "name": "Asia Pacific SE 6 (Manila)",      "lat":  14.599,  "lon":  120.984, "country_cca2": "PH", "geography": "Asia Pacific", "china_region": False},
    {"region_id": "ap-southeast-7",   "name": "Asia Pacific SE 7 (Bangkok)",     "lat":  13.756,  "lon":  100.502, "country_cca2": "TH", "geography": "Asia Pacific", "china_region": False},
    {"region_id": "ap-northeast-1",   "name": "Asia Pacific NE 1 (Tokyo)",       "lat":  35.617,  "lon":  139.746, "country_cca2": "JP", "geography": "Asia Pacific", "china_region": False},
    {"region_id": "ap-northeast-2",   "name": "Asia Pacific NE 2 (Seoul)",       "lat":  37.562,  "lon":  126.874, "country_cca2": "KR", "geography": "Asia Pacific", "china_region": False},
    {"region_id": "ap-south-1",       "name": "Asia Pacific S 1 (Mumbai)",       "lat":  19.243,  "lon":   72.967, "country_cca2": "IN", "geography": "Asia Pacific", "china_region": False},

    # Americas
    {"region_id": "us-west-1",        "name": "US West 1 (Silicon Valley)",      "lat":  37.388,  "lon": -122.059, "country_cca2": "US", "geography": "Americas",     "china_region": False},
    {"region_id": "us-east-1",        "name": "US East 1 (Virginia)",            "lat":  38.994,  "lon":  -77.452, "country_cca2": "US", "geography": "Americas",     "china_region": False},
    {"region_id": "sa-east-1",        "name": "South America E 1 (São Paulo)",   "lat": -23.493,  "lon":  -46.811, "country_cca2": "BR", "geography": "Americas",     "china_region": False},

    # Europe
    {"region_id": "eu-central-1",     "name": "EU Central 1 (Frankfurt)",        "lat":  50.099,  "lon":    8.630, "country_cca2": "DE", "geography": "Europe",       "china_region": False},
    {"region_id": "eu-west-1",        "name": "EU West 1 (London)",              "lat":  51.509,  "lon":   -0.061, "country_cca2": "GB", "geography": "Europe",       "china_region": False},

    # Middle East
    {"region_id": "me-east-1",        "name": "Middle East E 1 (Dubai)",         "lat":  25.205,  "lon":   55.271, "country_cca2": "AE", "geography": "Middle East",  "china_region": False},
    {"region_id": "me-central-1",     "name": "Middle East Central 1 (Riyadh)", "lat":  24.689,  "lon":   46.672, "country_cca2": "SA", "geography": "Middle East",  "china_region": False},

    # Africa
    {"region_id": "af-south-1",       "name": "Africa S 1 (Johannesburg)",       "lat": -26.195,  "lon":   28.034, "country_cca2": "ZA", "geography": "Africa",       "china_region": False},
]

TABLE_NAME = "alibaba_regions"


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
    for r in ALIBABA_REGIONS:
        client.put_item(
            TableName=TABLE_NAME,
            Item={
                "region_id":    {"S": r["region_id"]},
                "name":         {"S": r["name"]},
                "lat":          {"N": str(r["lat"])},
                "lon":          {"N": str(r["lon"])},
                "country_cca2": {"S": r["country_cca2"]},
                "geography":    {"S": r["geography"]},
                "china_region": {"BOOL": r["china_region"]},
            },
        )
    print(f"Seeded {len(ALIBABA_REGIONS)} Alibaba Cloud regions into {TABLE_NAME}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://localhost:4570")
    args = parser.parse_args()
    client = get_client(args.endpoint)
    ensure_table(client)
    seed(client)


if __name__ == "__main__":
    main()
