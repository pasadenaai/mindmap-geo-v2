#!/usr/bin/env python3
"""
Seed geo_elements table in LocalStack DynamoDB with all 118 periodic table elements.
Source: backend/data/elements.json (canonical; update that file to change element data).

Usage:
    python scripts/seed_elements.py
    python scripts/seed_elements.py --endpoint http://localhost:4570  # override endpoint
    python scripts/seed_elements.py --table my_elements_table
"""

from _local import LOCAL_CONFIG
import argparse
import json
import os
from decimal import Decimal
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

SCRIPT_DIR = Path(__file__).parent
DATA_FILE = SCRIPT_DIR.parent / "backend" / "data" / "elements.json"
TABLE_NAME = os.environ.get("DYNAMO_ELEMENTS_TABLE", "geo_elements")


def _to_dynamo(obj):
    """Recursively convert floats to Decimal for DynamoDB compatibility."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, int):
        return obj
    if isinstance(obj, dict):
        return {k: _to_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_dynamo(v) for v in obj]
    return obj


def main():
    parser = argparse.ArgumentParser(description="Seed geo_elements DynamoDB table")
    parser.add_argument(
        "--endpoint",
        default="http://localhost:4570",
        help="DynamoDB endpoint URL (default: http://localhost:4570)",
    )
    parser.add_argument(
        "--table",
        default=TABLE_NAME,
        help=f"DynamoDB table name (default: {TABLE_NAME})",
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region (default: us-east-1)",
    )
    args = parser.parse_args()

    elements = json.loads(DATA_FILE.read_text())
    print(f"Loaded {len(elements)} elements from {DATA_FILE}")

    dynamodb = boto3.resource(
        "dynamodb",
        endpoint_url=args.endpoint,
        region_name=args.region,
        config=LOCAL_CONFIG,
    )
    client = boto3.client(
        "dynamodb",
        endpoint_url=args.endpoint,
        region_name=args.region,
        config=LOCAL_CONFIG,
    )

    # Create table if it doesn't exist
    try:
        client.create_table(
            TableName=args.table,
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[{"AttributeName": "atomic_number", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "atomic_number", "KeyType": "HASH"}],
        )
        print(f"Created table {args.table}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"Table {args.table} already exists — upserting records")
        else:
            raise

    table = dynamodb.Table(args.table)

    with table.batch_writer() as batch:
        for element in elements:
            batch.put_item(Item=_to_dynamo(element))

    print(f"Seeded {len(elements)} elements into {args.table} at {args.endpoint}")


if __name__ == "__main__":
    main()
