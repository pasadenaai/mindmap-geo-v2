#!/usr/bin/env python3
"""
Sync DynamoDB tables between LocalStack (local dev) and real AWS DynamoDB.

Usage:
    # Push all tables from local → AWS (default)
    python scripts/sync_to_aws.py

    # Push specific tables only
    python scripts/sync_to_aws.py --tables geo_countries geo_elements geo_country_elements

    # Pull from AWS → local (useful for debugging with prod data)
    python scripts/sync_to_aws.py --direction aws-to-local

    # Dry run — print item counts without writing anything
    python scripts/sync_to_aws.py --dry-run

    # Custom LocalStack endpoint (default: http://localhost:4570)
    python scripts/sync_to_aws.py --local-endpoint http://localhost:4570

Prerequisites:
    - AWS credentials in environment or ~/.aws/credentials with DynamoDB access
    - IAM policy: pai-geo-seed (BatchWriteItem, PutItem, Scan, GetItem on geo_* tables)
    - LocalStack running locally (docker compose -f docker-compose.local.yaml up -d)
"""

from _local import LOCAL_CONFIG
import argparse
import sys
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

ALL_TABLES = [
    "geo_points",
    "geo_arcs",
    "geo_configs",
    "geo_countries",
    "aws_regions",
    "azure_regions",
    "gcp_regions",
    "alibaba_regions",
    "oci_regions",
    "ibm_regions",
    "geo_availability_zones",
    "geo_airlines",
    "geo_elements",
    "geo_country_elements",
    "geo_country_resources",
    "geo_ingest_sources",
    "geo_ingest_log",
]


def local_resource(endpoint: str):
    return boto3.resource(
        "dynamodb",
        endpoint_url=endpoint,
        region_name="us-east-1",
        config=LOCAL_CONFIG,
    )


def aws_resource():
    return boto3.resource("dynamodb", region_name="us-east-1")


def table_exists(resource, table_name: str) -> bool:
    try:
        resource.Table(table_name).load()
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            return False
        raise


def scan_all(table) -> list:
    """Full paginated scan — returns all items as Python dicts."""
    items = []
    kwargs: dict = {}
    while True:
        resp = table.scan(**kwargs)
        items.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    return items


def batch_write(table, items: list, dry_run: bool = False) -> int:
    """Write items in batches of 25 (DynamoDB hard limit)."""
    written = 0
    for i in range(0, len(items), 25):
        chunk = items[i : i + 25]
        if not dry_run:
            with table.batch_writer() as writer:
                for item in chunk:
                    writer.put_item(Item=item)
        written += len(chunk)
    return written


def sync_table(src, dst, src_name: str, dst_name: str, dry_run: bool = False) -> int:
    label = src_name if src_name == dst_name else f"{src_name} → {dst_name}"
    if not table_exists(src, src_name):
        print(f"  SKIP   {label:<45} — not found in source")
        return 0
    if not table_exists(dst, dst_name):
        print(f"  SKIP   {label:<45} — not found in destination (run CDK deploy?)")
        return 0

    items = scan_all(src.Table(src_name))
    if not items:
        print(f"  EMPTY  {label:<45} — 0 items")
        return 0

    written = batch_write(dst.Table(dst_name), items, dry_run=dry_run)
    tag = "dry-run" if dry_run else "wrote"
    print(f"  OK     {label:<45} — {tag} {written} items")
    return written


def main():
    parser = argparse.ArgumentParser(
        description="Sync geo DynamoDB tables between LocalStack and AWS"
    )
    parser.add_argument(
        "--direction",
        choices=["local-to-aws", "aws-to-local"],
        default="local-to-aws",
        help="Direction of sync (default: local-to-aws)",
    )
    parser.add_argument(
        "--tables",
        nargs="+",
        default=ALL_TABLES,
        metavar="TABLE",
        help="Tables to sync (default: all 17 geo tables)",
    )
    parser.add_argument(
        "--local-endpoint",
        default="http://localhost:4570",
        metavar="URL",
        help="LocalStack DynamoDB endpoint (default: http://localhost:4570)",
    )
    parser.add_argument(
        "--aws-prefix",
        default="",
        metavar="PREFIX",
        help="Prefix on AWS table names (the v2 stack uses 'v2_'); local names are never prefixed",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan source and print counts — no writes to destination",
    )
    args = parser.parse_args()

    try:
        local = local_resource(args.local_endpoint)
        aws = aws_resource()
        # Fail fast: verify AWS credentials before scanning anything. STS needs no DynamoDB
        # permission, so least-privilege deployer identities (no ListTables) work too.
        boto3.client("sts", region_name="us-east-1").get_caller_identity()
    except NoCredentialsError:
        print("ERROR: No AWS credentials found.", file=sys.stderr)
        print("       Set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY or configure ~/.aws/credentials", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Could not connect — {e}", file=sys.stderr)
        sys.exit(1)

    if args.direction == "local-to-aws":
        src, dst = local, aws
        print(f"Direction : LocalStack ({args.local_endpoint}) → AWS us-east-1")
    else:
        src, dst = aws, local
        print(f"Direction : AWS us-east-1 → LocalStack ({args.local_endpoint})")

    print(f"Tables    : {len(args.tables)}")
    print(f"Dry run   : {'yes' if args.dry_run else 'no'}")
    print()

    total = 0
    for table_name in args.tables:
        aws_name = args.aws_prefix + table_name
        if args.direction == "local-to-aws":
            total += sync_table(src, dst, table_name, aws_name, dry_run=args.dry_run)
        else:
            total += sync_table(src, dst, aws_name, table_name, dry_run=args.dry_run)

    print()
    print(f"Total items synced: {total}")


if __name__ == "__main__":
    main()
