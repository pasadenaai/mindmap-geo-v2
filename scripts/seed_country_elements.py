#!/usr/bin/env python3
"""Seed geo_country_elements DynamoDB table from backend/data/country_elements.json.

Usage (local):
    docker compose -f docker-compose.local.yaml exec backend \
        python /app/scripts/seed_country_elements.py

    Or run directly against LocalStack with:
    AWS_DEFAULT_REGION=us-east-1 \
    DYNAMODB_ENDPOINT_URL=http://localhost:4570 \
    python scripts/seed_country_elements.py
"""
from _local import LOCAL_AIO_CONFIG
import asyncio
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

import aioboto3

ENDPOINT_URL = os.environ.get("DYNAMODB_ENDPOINT_URL", "http://localhost:4570")
REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
TABLE = os.environ.get("DYNAMO_COUNTRY_ELEMENTS_TABLE", "geo_country_elements")

DATA_FILE = Path(__file__).parent.parent / "backend" / "data" / "country_elements.json"


def _to_dynamo(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _to_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_dynamo(v) for v in obj]
    return obj


async def seed():
    records = json.loads(DATA_FILE.read_text())
    session = aioboto3.Session()
    kwargs = {
        "region_name": REGION,
        "endpoint_url": ENDPOINT_URL,
        "config": LOCAL_AIO_CONFIG,
    }

    async with session.resource("dynamodb", **kwargs) as res:
        table = await res.Table(TABLE)
        written = 0
        for record in records:
            item = _to_dynamo(record)
            await table.put_item(Item=item)
            written += 1
            print(f"  ✓ {record['cca2']}  ({len(record['elements'])} elements)")

    print(f"\nSeeded {written} country-element records into '{TABLE}'.")


if __name__ == "__main__":
    try:
        asyncio.run(seed())
    except KeyboardInterrupt:
        sys.exit(0)
