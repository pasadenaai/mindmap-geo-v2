from fastapi import APIRouter, HTTPException
from typing import Optional
from app.models.schemas import (
    GeoPointCreate, GeoPointUpdate, GeoPointOut,
    GeoArcCreate, GeoArcUpdate, GeoArcOut,
    GlobeConfigCreate, GlobeConfigUpdate, GlobeConfigOut,
    CountryOut,
    AwsRegionOut, AwsRegionUpsert, AwsRegionBulkSync,
    AzureRegionOut, AzureRegionUpsert, AzureRegionBulkSync,
    GcpRegionOut, GcpRegionUpsert, GcpRegionBulkSync,
    AlibabaRegionOut, AlibabaRegionUpsert, AlibabaRegionBulkSync,
    OciRegionOut, OciRegionUpsert, OciRegionBulkSync,
    IbmRegionOut, IbmRegionUpsert, IbmRegionBulkSync,
    AirlineOut, AirlineUpsert, AirlineBulkSync,
    AvailabilityZoneOut, AvailabilityZoneUpsert, AvailabilityZoneBulkSync,
)
from app.repositories import dynamo

router = APIRouter(prefix="/geo", tags=["geo"])


# ── Geo Points ────────────────────────────────────────────────────────────────

@router.get("/points", response_model=list[GeoPointOut])
async def list_points():
    return await dynamo.list_points()


@router.post("/points", response_model=GeoPointOut, status_code=201)
async def create_point(body: GeoPointCreate):
    return await dynamo.create_point(body.model_dump())


@router.get("/points/{point_id}", response_model=GeoPointOut)
async def get_point(point_id: str):
    item = await dynamo.get_point(point_id)
    if not item:
        raise HTTPException(status_code=404, detail="Point not found")
    return item


@router.patch("/points/{point_id}", response_model=GeoPointOut)
async def update_point(point_id: str, body: GeoPointUpdate):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    item = await dynamo.update_point(point_id, updates)
    if not item:
        raise HTTPException(status_code=404, detail="Point not found")
    return item


@router.delete("/points/{point_id}", status_code=204)
async def delete_point(point_id: str):
    await dynamo.delete_point(point_id)


# ── Geo Arcs ──────────────────────────────────────────────────────────────────

@router.get("/arcs", response_model=list[GeoArcOut])
async def list_arcs():
    return await dynamo.list_arcs()


@router.post("/arcs", response_model=GeoArcOut, status_code=201)
async def create_arc(body: GeoArcCreate):
    return await dynamo.create_arc(body.model_dump())


@router.get("/arcs/{arc_id}", response_model=GeoArcOut)
async def get_arc(arc_id: str):
    item = await dynamo.get_arc(arc_id)
    if not item:
        raise HTTPException(status_code=404, detail="Arc not found")
    return item


@router.patch("/arcs/{arc_id}", response_model=GeoArcOut)
async def update_arc(arc_id: str, body: GeoArcUpdate):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    item = await dynamo.update_arc(arc_id, updates)
    if not item:
        raise HTTPException(status_code=404, detail="Arc not found")
    return item


@router.delete("/arcs/{arc_id}", status_code=204)
async def delete_arc(arc_id: str):
    await dynamo.delete_arc(arc_id)


# ── Globe Configs ─────────────────────────────────────────────────────────────

@router.get("/configs", response_model=list[GlobeConfigOut])
async def list_configs():
    return await dynamo.list_configs()


@router.post("/configs", response_model=GlobeConfigOut, status_code=201)
async def create_config(body: GlobeConfigCreate):
    return await dynamo.create_config(body.model_dump())


@router.get("/configs/{config_id}", response_model=GlobeConfigOut)
async def get_config(config_id: str):
    item = await dynamo.get_config(config_id)
    if not item:
        raise HTTPException(status_code=404, detail="Config not found")
    return item


@router.patch("/configs/{config_id}", response_model=GlobeConfigOut)
async def update_config(config_id: str, body: GlobeConfigUpdate):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    item = await dynamo.update_config(config_id, updates)
    if not item:
        raise HTTPException(status_code=404, detail="Config not found")
    return item


@router.delete("/configs/{config_id}", status_code=204)
async def delete_config(config_id: str):
    await dynamo.delete_config(config_id)


# ── Countries (read-only) ─────────────────────────────────────────────────────

@router.get("/countries", response_model=list[CountryOut])
async def list_countries():
    return await dynamo.list_countries()


@router.get("/countries/globe", response_model=list[CountryOut])
async def list_globe_countries():
    """All countries with a matching geometry in the 110m TopoJSON globe."""
    return await dynamo.list_globe_countries()


@router.get("/countries/by-feature/{ccn3}", response_model=CountryOut)
async def get_country_by_feature(ccn3: str):
    """Look up a country by its TopoJSON feature id (= ccn3). Used on globe click."""
    item = await dynamo.get_country_by_ccn3(ccn3)
    if not item:
        raise HTTPException(status_code=404, detail="Country not found")
    return item


@router.get("/countries/{cca2}", response_model=CountryOut)
async def get_country(cca2: str):
    item = await dynamo.get_country_by_cca2(cca2.upper())
    if not item:
        raise HTTPException(status_code=404, detail="Country not found")
    return item


# ── AWS Regions ───────────────────────────────────────────────────────────────

@router.get("/aws-regions", response_model=list[AwsRegionOut])
async def list_aws_regions():
    return await dynamo.list_aws_regions()


@router.get("/aws-regions/{region_id}", response_model=AwsRegionOut)
async def get_aws_region(region_id: str):
    item = await dynamo.get_aws_region(region_id)
    if not item:
        raise HTTPException(status_code=404, detail="AWS region not found")
    return item


@router.put("/aws-regions/{region_id}", response_model=AwsRegionOut)
async def upsert_aws_region(region_id: str, body: AwsRegionUpsert):
    if body.region_id != region_id:
        raise HTTPException(status_code=422, detail="region_id in path and body must match")
    return await dynamo.upsert_aws_region(body.model_dump())


@router.post("/aws-regions/sync", response_model=dict)
async def sync_aws_regions(body: AwsRegionBulkSync):
    count = await dynamo.upsert_aws_regions_bulk([r.model_dump() for r in body.regions])
    return {"synced": count}


@router.delete("/aws-regions/{region_id}", status_code=204)
async def delete_aws_region(region_id: str):
    await dynamo.delete_aws_region(region_id)


# ── Azure Regions ─────────────────────────────────────────────────────────────

@router.get("/azure-regions", response_model=list[AzureRegionOut])
async def list_azure_regions():
    return await dynamo.list_azure_regions()


@router.get("/azure-regions/{region_id}", response_model=AzureRegionOut)
async def get_azure_region(region_id: str):
    item = await dynamo.get_azure_region(region_id)
    if not item:
        raise HTTPException(status_code=404, detail="Azure region not found")
    return item


@router.put("/azure-regions/{region_id}", response_model=AzureRegionOut)
async def upsert_azure_region(region_id: str, body: AzureRegionUpsert):
    if body.region_id != region_id:
        raise HTTPException(status_code=422, detail="region_id in path and body must match")
    return await dynamo.upsert_azure_region(body.model_dump())


@router.post("/azure-regions/sync", response_model=dict)
async def sync_azure_regions(body: AzureRegionBulkSync):
    count = await dynamo.upsert_azure_regions_bulk([r.model_dump() for r in body.regions])
    return {"synced": count}


@router.delete("/azure-regions/{region_id}", status_code=204)
async def delete_azure_region(region_id: str):
    await dynamo.delete_azure_region(region_id)


# ── GCP Regions ───────────────────────────────────────────────────────────────

@router.get("/gcp-regions", response_model=list[GcpRegionOut])
async def list_gcp_regions():
    return await dynamo.list_gcp_regions()


@router.get("/gcp-regions/{region_id}", response_model=GcpRegionOut)
async def get_gcp_region(region_id: str):
    item = await dynamo.get_gcp_region(region_id)
    if not item:
        raise HTTPException(status_code=404, detail="GCP region not found")
    return item


@router.put("/gcp-regions/{region_id}", response_model=GcpRegionOut)
async def upsert_gcp_region(region_id: str, body: GcpRegionUpsert):
    if body.region_id != region_id:
        raise HTTPException(status_code=422, detail="region_id in path and body must match")
    return await dynamo.upsert_gcp_region(body.model_dump())


@router.post("/gcp-regions/sync", response_model=dict)
async def sync_gcp_regions(body: GcpRegionBulkSync):
    count = await dynamo.upsert_gcp_regions_bulk([r.model_dump() for r in body.regions])
    return {"synced": count}


@router.delete("/gcp-regions/{region_id}", status_code=204)
async def delete_gcp_region(region_id: str):
    await dynamo.delete_gcp_region(region_id)


# ── Alibaba Regions ───────────────────────────────────────────────────────────

@router.get("/alibaba-regions", response_model=list[AlibabaRegionOut])
async def list_alibaba_regions():
    return await dynamo.list_alibaba_regions()


@router.get("/alibaba-regions/{region_id}", response_model=AlibabaRegionOut)
async def get_alibaba_region(region_id: str):
    item = await dynamo.get_alibaba_region(region_id)
    if not item:
        raise HTTPException(status_code=404, detail="Alibaba region not found")
    return item


@router.put("/alibaba-regions/{region_id}", response_model=AlibabaRegionOut)
async def upsert_alibaba_region(region_id: str, body: AlibabaRegionUpsert):
    if body.region_id != region_id:
        raise HTTPException(status_code=422, detail="region_id in path and body must match")
    return await dynamo.upsert_alibaba_region(body.model_dump())


@router.post("/alibaba-regions/sync", response_model=dict)
async def sync_alibaba_regions(body: AlibabaRegionBulkSync):
    count = await dynamo.upsert_alibaba_regions_bulk([r.model_dump() for r in body.regions])
    return {"synced": count}


@router.delete("/alibaba-regions/{region_id}", status_code=204)
async def delete_alibaba_region(region_id: str):
    await dynamo.delete_alibaba_region(region_id)


# ── OCI Regions ───────────────────────────────────────────────────────────────

@router.get("/oci-regions", response_model=list[OciRegionOut])
async def list_oci_regions():
    return await dynamo.list_oci_regions()


@router.get("/oci-regions/{region_id}", response_model=OciRegionOut)
async def get_oci_region(region_id: str):
    item = await dynamo.get_oci_region(region_id)
    if not item:
        raise HTTPException(status_code=404, detail="OCI region not found")
    return item


@router.put("/oci-regions/{region_id}", response_model=OciRegionOut)
async def upsert_oci_region(region_id: str, body: OciRegionUpsert):
    if body.region_id != region_id:
        raise HTTPException(status_code=422, detail="region_id in path and body must match")
    return await dynamo.upsert_oci_region(body.model_dump())


@router.post("/oci-regions/sync", response_model=dict)
async def sync_oci_regions(body: OciRegionBulkSync):
    count = await dynamo.upsert_oci_regions_bulk([r.model_dump() for r in body.regions])
    return {"synced": count}


@router.delete("/oci-regions/{region_id}", status_code=204)
async def delete_oci_region(region_id: str):
    await dynamo.delete_oci_region(region_id)


# ── IBM Regions ───────────────────────────────────────────────────────────────

@router.get("/ibm-regions", response_model=list[IbmRegionOut])
async def list_ibm_regions():
    return await dynamo.list_ibm_regions()


@router.get("/ibm-regions/{region_id}", response_model=IbmRegionOut)
async def get_ibm_region(region_id: str):
    item = await dynamo.get_ibm_region(region_id)
    if not item:
        raise HTTPException(status_code=404, detail="IBM region not found")
    return item


@router.put("/ibm-regions/{region_id}", response_model=IbmRegionOut)
async def upsert_ibm_region(region_id: str, body: IbmRegionUpsert):
    if body.region_id != region_id:
        raise HTTPException(status_code=422, detail="region_id in path and body must match")
    return await dynamo.upsert_ibm_region(body.model_dump())


@router.post("/ibm-regions/sync", response_model=dict)
async def sync_ibm_regions(body: IbmRegionBulkSync):
    count = await dynamo.upsert_ibm_regions_bulk([r.model_dump() for r in body.regions])
    return {"synced": count}


@router.delete("/ibm-regions/{region_id}", status_code=204)
async def delete_ibm_region(region_id: str):
    await dynamo.delete_ibm_region(region_id)


# ── Availability Zones (shared across all providers) ──────────────────────────

@router.get("/availability-zones", response_model=list[AvailabilityZoneOut])
async def list_availability_zones(
    provider: Optional[str] = None,
    region_id: Optional[str] = None,
):
    """List AZs. Filter by ?provider=aws or ?provider=aws&region_id=us-east-1."""
    return await dynamo.list_availability_zones(provider=provider, region_id=region_id)


@router.get("/availability-zones/{az_id:path}", response_model=AvailabilityZoneOut)
async def get_availability_zone(az_id: str):
    item = await dynamo.get_availability_zone(az_id)
    if not item:
        raise HTTPException(status_code=404, detail="Availability zone not found")
    return item


@router.put("/availability-zones", response_model=AvailabilityZoneOut)
async def upsert_availability_zone(body: AvailabilityZoneUpsert):
    """Upsert a single AZ. az_id is derived from provider + region_id + az_name."""
    return await dynamo.upsert_availability_zone(body.model_dump())


@router.post("/availability-zones/sync", response_model=dict)
async def sync_availability_zones(body: AvailabilityZoneBulkSync):
    """Bulk-upsert AZs across any provider. Used by the periodic sync cron."""
    count = await dynamo.upsert_availability_zones_bulk([z.model_dump() for z in body.zones])
    return {"synced": count}


@router.delete("/availability-zones/{az_id:path}", status_code=204)
async def delete_availability_zone(az_id: str):
    await dynamo.delete_availability_zone(az_id)


# ── Airlines ──────────────────────────────────────────────────────────────────

@router.get("/airlines", response_model=list[AirlineOut])
async def list_airlines():
    """List all airlines. Active status is populated by the periodic sync cron."""
    return await dynamo.list_airlines()


@router.get("/airlines/{iata}", response_model=AirlineOut)
async def get_airline(iata: str):
    item = await dynamo.get_airline(iata)
    if not item:
        raise HTTPException(status_code=404, detail="Airline not found")
    return item


@router.put("/airlines/{iata}", response_model=AirlineOut)
async def upsert_airline(iata: str, body: AirlineUpsert):
    """Insert or replace a single airline record. Used by the cron to update active status."""
    if body.iata.upper() != iata.upper():
        raise HTTPException(status_code=422, detail="IATA in path and body must match")
    return await dynamo.upsert_airline(body.model_dump())


@router.post("/airlines/sync", response_model=dict)
async def sync_airlines(body: AirlineBulkSync):
    """Bulk-upsert airline records. Intended for the periodic active-status cron job."""
    count = await dynamo.upsert_airlines_bulk([a.model_dump() for a in body.airlines])
    return {"synced": count}


@router.delete("/airlines/{iata}", status_code=204)
async def delete_airline(iata: str):
    await dynamo.delete_airline(iata)
