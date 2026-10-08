"""DynamoDB repository for geo data.

Tables are auto-created on startup if they don't exist (LocalStack or real AWS).
All operations are async via aioboto3.
"""
from __future__ import annotations
import uuid
import logging
from decimal import Decimal
import aioboto3
from aiobotocore.config import AioConfig
from boto3.dynamodb.conditions import Attr
from botocore import UNSIGNED
from botocore.exceptions import ClientError
from app.core.config import settings

logger = logging.getLogger(__name__)

_session: aioboto3.Session | None = None


def _get_session() -> aioboto3.Session:
    global _session
    if _session is None:
        _session = aioboto3.Session()
    return _session


def _client_kwargs() -> dict:
    kwargs: dict = {"region_name": settings.aws_region}
    if settings.dynamodb_endpoint_url:
        kwargs["endpoint_url"] = settings.dynamodb_endpoint_url
        # LocalStack does not authenticate; send unsigned instead of dummy credentials
        kwargs["config"] = AioConfig(signature_version=UNSIGNED)
    return kwargs


async def ensure_tables() -> None:
    """Create DynamoDB tables if they don't already exist."""
    async with _get_session().client("dynamodb", **_client_kwargs()) as client:
        # geo_users needs a GSI on username — created separately
        try:
            await client.create_table(
                TableName=settings.dynamo_users_table,
                BillingMode="PAY_PER_REQUEST",
                AttributeDefinitions=[
                    {"AttributeName": "user_id", "AttributeType": "S"},
                    {"AttributeName": "username", "AttributeType": "S"},
                ],
                KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
                GlobalSecondaryIndexes=[{
                    "IndexName": "username-index",
                    "KeySchema": [{"AttributeName": "username", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                }],
            )
            logger.info("Created table %s", settings.dynamo_users_table)
        except ClientError as e:
            if e.response["Error"]["Code"] != "ResourceInUseException":
                raise

    tables = [
        (settings.dynamo_geo_points_table, "point_id"),
        (settings.dynamo_geo_arcs_table, "arc_id"),
        (settings.dynamo_geo_configs_table, "config_id"),
        (settings.dynamo_airlines_table, "iata"),
        (settings.dynamo_availability_zones_table, "az_id"),
        (settings.dynamo_elements_table, "atomic_number"),
        (settings.dynamo_country_elements_table, "cca2"),
        (settings.dynamo_country_resources_table, "cca2"),
        (settings.dynamo_ingest_sources_table, "source_id"),
        (settings.dynamo_ingest_log_table, "run_id"),
    ]
    async with _get_session().client("dynamodb", **_client_kwargs()) as client:
        for table_name, pk in tables:
            try:
                await client.create_table(
                    TableName=table_name,
                    BillingMode="PAY_PER_REQUEST",
                    AttributeDefinitions=[{"AttributeName": pk, "AttributeType": "S"}],
                    KeySchema=[{"AttributeName": pk, "KeyType": "HASH"}],
                )
                logger.info("Created table %s", table_name)
            except ClientError as e:
                if e.response["Error"]["Code"] != "ResourceInUseException":
                    raise


# ── Serialization helpers ─────────────────────────────────────────────────────

def _to_dynamo(obj):
    """Recursively convert floats to Decimal for DynamoDB compatibility."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _to_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_dynamo(v) for v in obj]
    return obj


# ── Generic helpers ───────────────────────────────────────────────────────────

async def _put(table: str, item: dict) -> dict:
    async with _get_session().resource("dynamodb", **_client_kwargs()) as res:
        tbl = await res.Table(table)
        await tbl.put_item(Item=_to_dynamo(item))
    return item


async def _get(table: str, pk_name: str, pk_val: str) -> dict | None:
    async with _get_session().resource("dynamodb", **_client_kwargs()) as res:
        tbl = await res.Table(table)
        resp = await tbl.get_item(Key={pk_name: pk_val})
    return resp.get("Item")


async def _list(table: str) -> list[dict]:
    async with _get_session().resource("dynamodb", **_client_kwargs()) as res:
        tbl = await res.Table(table)
        resp = await tbl.scan()
    return resp.get("Items", [])


async def _delete(table: str, pk_name: str, pk_val: str) -> None:
    async with _get_session().resource("dynamodb", **_client_kwargs()) as res:
        tbl = await res.Table(table)
        await tbl.delete_item(Key={pk_name: pk_val})


async def _update(table: str, pk_name: str, pk_val: str, updates: dict) -> dict | None:
    if not updates:
        return await _get(table, pk_name, pk_val)

    expr_parts, attr_vals, attr_names = [], {}, {}
    for i, (k, v) in enumerate(updates.items()):
        placeholder = f":v{i}"
        name_token = f"#n{i}"
        expr_parts.append(f"{name_token} = {placeholder}")
        attr_vals[placeholder] = v
        attr_names[name_token] = k

    async with _get_session().resource("dynamodb", **_client_kwargs()) as res:
        tbl = await res.Table(table)
        resp = await tbl.update_item(
            Key={pk_name: pk_val},
            UpdateExpression="SET " + ", ".join(expr_parts),
            ExpressionAttributeValues=attr_vals,
            ExpressionAttributeNames=attr_names,
            ReturnValues="ALL_NEW",
        )
    return resp.get("Attributes")


# ── Geo Points ────────────────────────────────────────────────────────────────

async def create_point(data: dict) -> dict:
    item = {"point_id": str(uuid.uuid4()), **data}
    return await _put(settings.dynamo_geo_points_table, item)


async def get_point(point_id: str) -> dict | None:
    return await _get(settings.dynamo_geo_points_table, "point_id", point_id)


async def list_points() -> list[dict]:
    return await _list(settings.dynamo_geo_points_table)


async def update_point(point_id: str, updates: dict) -> dict | None:
    return await _update(settings.dynamo_geo_points_table, "point_id", point_id, updates)


async def delete_point(point_id: str) -> None:
    await _delete(settings.dynamo_geo_points_table, "point_id", point_id)


# ── Geo Arcs ──────────────────────────────────────────────────────────────────

async def create_arc(data: dict) -> dict:
    item = {"arc_id": str(uuid.uuid4()), **data}
    return await _put(settings.dynamo_geo_arcs_table, item)


async def get_arc(arc_id: str) -> dict | None:
    return await _get(settings.dynamo_geo_arcs_table, "arc_id", arc_id)


async def list_arcs() -> list[dict]:
    return await _list(settings.dynamo_geo_arcs_table)


async def update_arc(arc_id: str, updates: dict) -> dict | None:
    return await _update(settings.dynamo_geo_arcs_table, "arc_id", arc_id, updates)


async def delete_arc(arc_id: str) -> None:
    await _delete(settings.dynamo_geo_arcs_table, "arc_id", arc_id)


# ── Globe Configs ─────────────────────────────────────────────────────────────

async def create_config(data: dict) -> dict:
    item = {"config_id": str(uuid.uuid4()), **data}
    return await _put(settings.dynamo_geo_configs_table, item)


async def get_config(config_id: str) -> dict | None:
    return await _get(settings.dynamo_geo_configs_table, "config_id", config_id)


async def list_configs() -> list[dict]:
    return await _list(settings.dynamo_geo_configs_table)


async def update_config(config_id: str, updates: dict) -> dict | None:
    return await _update(settings.dynamo_geo_configs_table, "config_id", config_id, updates)


async def delete_config(config_id: str) -> None:
    await _delete(settings.dynamo_geo_configs_table, "config_id", config_id)


# ── Countries (read-only reference data) ──────────────────────────────────────

async def list_countries() -> list[dict]:
    return await _list(settings.dynamo_geo_countries_table)


async def list_globe_countries() -> list[dict]:
    """Return only countries that have a matching TopoJSON geometry on the globe."""
    async with _get_session().resource("dynamodb", **_client_kwargs()) as res:
        tbl = await res.Table(settings.dynamo_geo_countries_table)
        resp = await tbl.scan(FilterExpression=Attr("has_globe_geometry").eq(True))
    items = resp.get("Items", [])
    return sorted(items, key=lambda c: c.get("name_common", ""))


async def get_country_by_cca2(cca2: str) -> dict | None:
    return await _get(settings.dynamo_geo_countries_table, "cca2", cca2)


async def get_country_by_ccn3(ccn3: str) -> dict | None:
    """Lookup by TopoJSON feature id (= ccn3). Used when a globe feature is clicked."""
    async with _get_session().resource("dynamodb", **_client_kwargs()) as res:
        tbl = await res.Table(settings.dynamo_geo_countries_table)
        resp = await tbl.scan(FilterExpression=Attr("ccn3").eq(ccn3))
    items = resp.get("Items", [])
    return items[0] if items else None


# ── AWS Regions (read-only reference data) ────────────────────────────────────

async def list_aws_regions() -> list[dict]:
    items = await _list(settings.dynamo_aws_regions_table)
    return sorted(items, key=lambda r: r.get("region_id", ""))


async def get_aws_region(region_id: str) -> dict | None:
    return await _get(settings.dynamo_aws_regions_table, "region_id", region_id)


# ── Azure Regions (read-only reference data) ──────────────────────────────────

async def list_azure_regions() -> list[dict]:
    items = await _list(settings.dynamo_azure_regions_table)
    return sorted(items, key=lambda r: r.get("region_id", ""))


async def get_azure_region(region_id: str) -> dict | None:
    return await _get(settings.dynamo_azure_regions_table, "region_id", region_id)


# ── GCP Regions ───────────────────────────────────────────────────────────────

async def list_gcp_regions() -> list[dict]:
    items = await _list(settings.dynamo_gcp_regions_table)
    return sorted(items, key=lambda r: r.get("region_id", ""))


async def get_gcp_region(region_id: str) -> dict | None:
    return await _get(settings.dynamo_gcp_regions_table, "region_id", region_id)


# ── Alibaba Regions ───────────────────────────────────────────────────────────

async def list_alibaba_regions() -> list[dict]:
    items = await _list(settings.dynamo_alibaba_regions_table)
    return sorted(items, key=lambda r: r.get("region_id", ""))


async def get_alibaba_region(region_id: str) -> dict | None:
    return await _get(settings.dynamo_alibaba_regions_table, "region_id", region_id)


# ── OCI Regions ───────────────────────────────────────────────────────────────

async def list_oci_regions() -> list[dict]:
    items = await _list(settings.dynamo_oci_regions_table)
    return sorted(items, key=lambda r: r.get("region_id", ""))


async def get_oci_region(region_id: str) -> dict | None:
    return await _get(settings.dynamo_oci_regions_table, "region_id", region_id)


# ── IBM Regions ───────────────────────────────────────────────────────────────

async def list_ibm_regions() -> list[dict]:
    items = await _list(settings.dynamo_ibm_regions_table)
    return sorted(items, key=lambda r: r.get("region_id", ""))


async def get_ibm_region(region_id: str) -> dict | None:
    return await _get(settings.dynamo_ibm_regions_table, "region_id", region_id)


# ── Airlines ──────────────────────────────────────────────────────────────────

async def list_airlines() -> list[dict]:
    items = await _list(settings.dynamo_airlines_table)
    return sorted(items, key=lambda a: a.get("name", ""))


async def get_airline(iata: str) -> dict | None:
    return await _get(settings.dynamo_airlines_table, "iata", iata.upper())


async def upsert_airline(data: dict) -> dict:
    """Insert or fully replace an airline record keyed by IATA code."""
    item = {**data, "iata": data["iata"].upper()}
    return await _put(settings.dynamo_airlines_table, item)


async def upsert_airlines_bulk(records: list[dict]) -> int:
    """Batch-upsert a list of airline records. Returns count written."""
    async with _get_session().resource("dynamodb", **_client_kwargs()) as res:
        tbl = await res.Table(settings.dynamo_airlines_table)
        async with tbl.batch_writer() as batch:
            for record in records:
                await batch.put_item(Item={**record, "iata": record["iata"].upper()})
    return len(records)


async def delete_airline(iata: str) -> None:
    await _delete(settings.dynamo_airlines_table, "iata", iata.upper())


# ── Cloud region upsert / delete helpers ──────────────────────────────────────

async def _upsert_region(table: str, pk: str, data: dict) -> dict:
    return await _put(table, data)


async def _upsert_regions_bulk(table: str, records: list[dict]) -> int:
    async with _get_session().resource("dynamodb", **_client_kwargs()) as res:
        tbl = await res.Table(table)
        async with tbl.batch_writer() as batch:
            for record in records:
                await batch.put_item(Item=_to_dynamo(record))
    return len(records)


async def _delete_region(table: str, pk: str, pk_val: str) -> None:
    await _delete(table, pk, pk_val)


# AWS
async def upsert_aws_region(data: dict) -> dict:
    return await _upsert_region(settings.dynamo_aws_regions_table, "region_id", data)


async def upsert_aws_regions_bulk(records: list[dict]) -> int:
    return await _upsert_regions_bulk(settings.dynamo_aws_regions_table, records)


async def delete_aws_region(region_id: str) -> None:
    await _delete_region(settings.dynamo_aws_regions_table, "region_id", region_id)


# Azure
async def upsert_azure_region(data: dict) -> dict:
    return await _upsert_region(settings.dynamo_azure_regions_table, "region_id", data)


async def upsert_azure_regions_bulk(records: list[dict]) -> int:
    return await _upsert_regions_bulk(settings.dynamo_azure_regions_table, records)


async def delete_azure_region(region_id: str) -> None:
    await _delete_region(settings.dynamo_azure_regions_table, "region_id", region_id)


# GCP
async def upsert_gcp_region(data: dict) -> dict:
    return await _upsert_region(settings.dynamo_gcp_regions_table, "region_id", data)


async def upsert_gcp_regions_bulk(records: list[dict]) -> int:
    return await _upsert_regions_bulk(settings.dynamo_gcp_regions_table, records)


async def delete_gcp_region(region_id: str) -> None:
    await _delete_region(settings.dynamo_gcp_regions_table, "region_id", region_id)


# Alibaba
async def upsert_alibaba_region(data: dict) -> dict:
    return await _upsert_region(settings.dynamo_alibaba_regions_table, "region_id", data)


async def upsert_alibaba_regions_bulk(records: list[dict]) -> int:
    return await _upsert_regions_bulk(settings.dynamo_alibaba_regions_table, records)


async def delete_alibaba_region(region_id: str) -> None:
    await _delete_region(settings.dynamo_alibaba_regions_table, "region_id", region_id)


# OCI
async def upsert_oci_region(data: dict) -> dict:
    return await _upsert_region(settings.dynamo_oci_regions_table, "region_id", data)


async def upsert_oci_regions_bulk(records: list[dict]) -> int:
    return await _upsert_regions_bulk(settings.dynamo_oci_regions_table, records)


async def delete_oci_region(region_id: str) -> None:
    await _delete_region(settings.dynamo_oci_regions_table, "region_id", region_id)


# IBM
async def upsert_ibm_region(data: dict) -> dict:
    return await _upsert_region(settings.dynamo_ibm_regions_table, "region_id", data)


async def upsert_ibm_regions_bulk(records: list[dict]) -> int:
    return await _upsert_regions_bulk(settings.dynamo_ibm_regions_table, records)


async def delete_ibm_region(region_id: str) -> None:
    await _delete_region(settings.dynamo_ibm_regions_table, "region_id", region_id)


# ── Availability Zones ────────────────────────────────────────────────────────

def _az_id(provider: str, region_id: str, az_name: str) -> str:
    return f"{provider}:{region_id}:{az_name}"


async def list_availability_zones(provider: str | None = None, region_id: str | None = None) -> list[dict]:
    async with _get_session().resource("dynamodb", **_client_kwargs()) as res:
        tbl = await res.Table(settings.dynamo_availability_zones_table)
        filter_expr = None
        if provider and region_id:
            filter_expr = Attr("provider").eq(provider) & Attr("region_id").eq(region_id)
        elif provider:
            filter_expr = Attr("provider").eq(provider)
        elif region_id:
            filter_expr = Attr("region_id").eq(region_id)
        kwargs = {"FilterExpression": filter_expr} if filter_expr else {}
        resp = await tbl.scan(**kwargs)
    items = resp.get("Items", [])
    return sorted(items, key=lambda z: z.get("az_id", ""))


async def get_availability_zone(az_id: str) -> dict | None:
    return await _get(settings.dynamo_availability_zones_table, "az_id", az_id)


async def upsert_availability_zone(data: dict) -> dict:
    item = {
        **data,
        "az_id": _az_id(data["provider"], data["region_id"], data["az_name"]),
    }
    return await _put(settings.dynamo_availability_zones_table, item)


async def upsert_availability_zones_bulk(records: list[dict]) -> int:
    async with _get_session().resource("dynamodb", **_client_kwargs()) as res:
        tbl = await res.Table(settings.dynamo_availability_zones_table)
        async with tbl.batch_writer() as batch:
            for record in records:
                item = _to_dynamo({
                    **record,
                    "az_id": _az_id(record["provider"], record["region_id"], record["az_name"]),
                })
                await batch.put_item(Item=item)
    return len(records)


async def delete_availability_zone(az_id: str) -> None:
    await _delete(settings.dynamo_availability_zones_table, "az_id", az_id)


# ── Periodic Table Elements ───────────────────────────────────────────────────

async def list_elements() -> list[dict]:
    items = await _list(settings.dynamo_elements_table)
    return sorted(items, key=lambda e: int(e.get("atomic_number_int", e.get("atomic_number", 0))))


async def get_element(atomic_number: str) -> dict | None:
    return await _get(settings.dynamo_elements_table, "atomic_number", atomic_number)


async def get_element_by_symbol(symbol: str) -> dict | None:
    async with _get_session().resource("dynamodb", **_client_kwargs()) as res:
        tbl = await res.Table(settings.dynamo_elements_table)
        resp = await tbl.scan(FilterExpression=Attr("symbol").eq(symbol.capitalize()))
    items = resp.get("Items", [])
    return items[0] if items else None


async def upsert_element(data: dict) -> dict:
    """Insert or fully replace an element record keyed by atomic_number string."""
    item = {**data, "atomic_number": str(data["atomic_number"])}
    return await _put(settings.dynamo_elements_table, item)


# ── Country elements ──────────────────────────────────────────────────────────

async def get_country_elements(cca2: str) -> dict | None:
    """Return the element-reserve profile for a country, keyed by ISO alpha-2."""
    return await _get(settings.dynamo_country_elements_table, "cca2", cca2.upper())


async def upsert_country_elements(data: dict) -> dict:
    """Insert or fully replace a country-elements record keyed by cca2."""
    item = {**data, "cca2": str(data["cca2"]).upper()}
    return await _put(settings.dynamo_country_elements_table, item)


# ── Country natural resources (Phase 2 — EIA oil/gas/coal) ───────────────────

async def get_country_resources(cca2: str) -> dict | None:
    return await _get(settings.dynamo_country_resources_table, "cca2", cca2.upper())


async def upsert_country_resources(data: dict) -> dict:
    item = {**data, "cca2": str(data["cca2"]).upper()}
    return await _put(settings.dynamo_country_resources_table, item)


async def list_country_resources() -> list[dict]:
    return await _list(settings.dynamo_country_resources_table)


# ── Ingest source registry ────────────────────────────────────────────────────

async def list_ingest_sources() -> list[dict]:
    items = await _list(settings.dynamo_ingest_sources_table)
    return sorted(items, key=lambda s: s.get("source_id", ""))


async def get_ingest_source(source_id: str) -> dict | None:
    return await _get(settings.dynamo_ingest_sources_table, "source_id", source_id)


async def upsert_ingest_source(data: dict) -> dict:
    return await _put(settings.dynamo_ingest_sources_table, _to_dynamo(data))


# ── Ingest log ────────────────────────────────────────────────────────────────

async def create_ingest_log(data: dict) -> dict:
    item = {"run_id": str(uuid.uuid4()), **data}
    return await _put(settings.dynamo_ingest_log_table, _to_dynamo(item))


async def update_ingest_log(run_id: str, updates: dict) -> dict | None:
    return await _update(settings.dynamo_ingest_log_table, "run_id", run_id, _to_dynamo(updates))


async def get_ingest_log(run_id: str) -> dict | None:
    return await _get(settings.dynamo_ingest_log_table, "run_id", run_id)


async def list_ingest_logs(limit: int = 50) -> list[dict]:
    items = await _list(settings.dynamo_ingest_log_table)
    items.sort(key=lambda r: r.get("started_at", ""), reverse=True)
    return items[:limit]


# ── Users ─────────────────────────────────────────────────────────────────────

from datetime import datetime, timezone

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_user(username: str, hashed_password: str) -> dict:
    item = {
        "user_id": str(uuid.uuid4()),
        "username": username,
        "hashed_password": hashed_password,
        "created_at": _now_iso(),
    }
    return await _put(settings.dynamo_users_table, item)


async def get_user_by_username(username: str) -> dict | None:
    from boto3.dynamodb.conditions import Key
    async with _get_session().resource("dynamodb", **_client_kwargs()) as res:
        tbl = await res.Table(settings.dynamo_users_table)
        resp = await tbl.query(
            IndexName="username-index",
            KeyConditionExpression=Key("username").eq(username),
        )
    items = resp.get("Items", [])
    return items[0] if items else None


async def get_user_by_id(user_id: str) -> dict | None:
    return await _get(settings.dynamo_users_table, "user_id", user_id)
