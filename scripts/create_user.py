#!/usr/bin/env python3
"""Create a user directly in DynamoDB (registration is closed by default).

Uses the normal boto3 credential chain against real AWS unless --endpoint is given
(LocalStack, sent unsigned). The password is read from a hidden prompt, never argv.

Usage:
    python scripts/create_user.py alice
    python scripts/create_user.py alice --endpoint http://localhost:4570
"""
import argparse
import getpass
import sys
import uuid
from datetime import datetime, timezone

import bcrypt
import boto3
from boto3.dynamodb.conditions import Key

MIN_LEN = 12


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("username")
    ap.add_argument("--table", default="geo_users", help="users table (the v2 AWS stack uses v2_geo_users)")
    ap.add_argument("--region", default="us-east-1")
    ap.add_argument("--endpoint", default=None, help="LocalStack endpoint; omit for real AWS")
    args = ap.parse_args()

    if not 3 <= len(args.username) <= 32:
        print("ERROR: username must be 3-32 characters", file=sys.stderr)
        return 1
    pw = getpass.getpass("Password: ")
    if pw != getpass.getpass("Confirm: "):
        print("ERROR: passwords do not match", file=sys.stderr)
        return 1
    if not MIN_LEN <= len(pw) <= 128 or args.username.lower() in pw.lower():
        print(f"ERROR: password must be {MIN_LEN}-128 chars and not contain the username", file=sys.stderr)
        return 1

    kwargs = {"region_name": args.region}
    if args.endpoint:
        from _local import LOCAL_CONFIG
        kwargs.update(endpoint_url=args.endpoint, config=LOCAL_CONFIG)
    table = boto3.resource("dynamodb", **kwargs).Table(args.table)

    if table.query(IndexName="username-index",
                   KeyConditionExpression=Key("username").eq(args.username))["Items"]:
        print("ERROR: username already exists", file=sys.stderr)
        return 1
    table.put_item(Item={
        "user_id": str(uuid.uuid4()),
        "username": args.username,
        "hashed_password": bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    print(f"created user {args.username}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
