from __future__ import annotations
from typing import Optional, Any, Literal
from pydantic import BaseModel, Field
import uuid


# ── Auth ─────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    # NIST 800-63B: length over composition rules
    password: str = Field(..., min_length=12, max_length=128)


class LoginIn(BaseModel):
    # No min length here so validation errors don't reveal the password policy to attackers
    username: str = Field(..., max_length=32)
    password: str = Field(..., max_length=128)


class UserOut(BaseModel):
    user_id: str
    username: str
    created_at: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ── Geo Point ────────────────────────────────────────────────────────────────

class GeoPointCreate(BaseModel):
    label: str
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    color: str = "#4fc3f7"
    size: float = Field(default=1.0, gt=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GeoPointUpdate(BaseModel):
    label: Optional[str] = None
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lon: Optional[float] = Field(default=None, ge=-180, le=180)
    color: Optional[str] = None
    size: Optional[float] = Field(default=None, gt=0)
    metadata: Optional[dict[str, Any]] = None


class GeoPointOut(BaseModel):
    point_id: str
    label: str
    lat: float
    lon: float
    color: str
    size: float
    metadata: dict[str, Any]


# ── Geo Arc ──────────────────────────────────────────────────────────────────

class GeoArcCreate(BaseModel):
    label: Optional[str] = None
    start_lat: float = Field(..., ge=-90, le=90)
    start_lon: float = Field(..., ge=-180, le=180)
    end_lat: float = Field(..., ge=-90, le=90)
    end_lon: float = Field(..., ge=-180, le=180)
    color: str = "#4fc3f7"
    altitude: float = Field(default=0.3, ge=0, le=2.0)


class GeoArcUpdate(BaseModel):
    label: Optional[str] = None
    color: Optional[str] = None
    altitude: Optional[float] = Field(default=None, ge=0, le=2.0)


class GeoArcOut(BaseModel):
    arc_id: str
    label: Optional[str]
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    color: str
    altitude: float


# ── Country ──────────────────────────────────────────────────────────────────

class CountryOut(BaseModel):
    cca2: str
    cca3: str
    ccn3: Optional[str] = None
    name_common: str
    name_official: str
    region: str
    subregion: str
    flag_1x1: Optional[str] = None
    flag_4x3: Optional[str] = None
    has_globe_geometry: bool = False
    globe_feature_id: Optional[str] = None


# ── Shared region status ──────────────────────────────────────────────────────
# status lifecycle: "ga" → generally available, "planned" → announced with no
# launch date, "announced" → launch date known, "deprecated" → shutting down.
REGION_STATUS = Literal["ga", "planned", "announced", "deprecated"]


# ── AWS Region ───────────────────────────────────────────────────────────────

class AwsRegionOut(BaseModel):
    region_id: str
    name: str
    lat: float
    lon: float
    country_cca2: str
    geography: str
    opt_in_required: bool
    az_count: int
    status: str = "ga"
    last_updated: Optional[str] = None


class AwsRegionUpsert(BaseModel):
    region_id: str
    name: str
    lat: float
    lon: float
    country_cca2: str
    geography: str
    opt_in_required: bool = False
    az_count: int = 0
    status: REGION_STATUS = "ga"
    last_updated: Optional[str] = None


class AwsRegionBulkSync(BaseModel):
    regions: list[AwsRegionUpsert]


# ── Azure Region ─────────────────────────────────────────────────────────────

class AzureRegionOut(BaseModel):
    region_id: str
    name: str
    physical_location: str
    country_cca2: str
    geography: str
    lat: float
    lon: float
    has_az: bool
    restricted: bool
    status: str = "ga"
    last_updated: Optional[str] = None


class AzureRegionUpsert(BaseModel):
    region_id: str
    name: str
    physical_location: str
    country_cca2: str
    geography: str
    lat: float
    lon: float
    has_az: bool = False
    restricted: bool = False
    status: REGION_STATUS = "ga"
    last_updated: Optional[str] = None


class AzureRegionBulkSync(BaseModel):
    regions: list[AzureRegionUpsert]


# ── GCP Region ───────────────────────────────────────────────────────────────

class GcpRegionOut(BaseModel):
    region_id: str
    name: str
    lat: float
    lon: float
    country_cca2: str
    geography: str
    zone_count: int
    status: str = "ga"
    last_updated: Optional[str] = None


class GcpRegionUpsert(BaseModel):
    region_id: str
    name: str
    lat: float
    lon: float
    country_cca2: str
    geography: str
    zone_count: int = 0
    status: REGION_STATUS = "ga"
    last_updated: Optional[str] = None


class GcpRegionBulkSync(BaseModel):
    regions: list[GcpRegionUpsert]


# ── Alibaba Region ────────────────────────────────────────────────────────────

class AlibabaRegionOut(BaseModel):
    region_id: str
    name: str
    lat: float
    lon: float
    country_cca2: str
    geography: str
    china_region: bool
    status: str = "ga"
    last_updated: Optional[str] = None


class AlibabaRegionUpsert(BaseModel):
    region_id: str
    name: str
    lat: float
    lon: float
    country_cca2: str
    geography: str
    china_region: bool = False
    status: REGION_STATUS = "ga"
    last_updated: Optional[str] = None


class AlibabaRegionBulkSync(BaseModel):
    regions: list[AlibabaRegionUpsert]


# ── OCI Region ────────────────────────────────────────────────────────────────

class OciRegionOut(BaseModel):
    region_id: str
    name: str
    lat: float
    lon: float
    country_cca2: str
    geography: str
    realm: str
    status: str = "ga"
    last_updated: Optional[str] = None


class OciRegionUpsert(BaseModel):
    region_id: str
    name: str
    lat: float
    lon: float
    country_cca2: str
    geography: str
    realm: str
    status: REGION_STATUS = "ga"
    last_updated: Optional[str] = None


class OciRegionBulkSync(BaseModel):
    regions: list[OciRegionUpsert]


# ── IBM Region ────────────────────────────────────────────────────────────────

class IbmRegionOut(BaseModel):
    region_id: str
    name: str
    lat: float
    lon: float
    country_cca2: str
    geography: str
    kind: str
    status: str = "ga"
    last_updated: Optional[str] = None


class IbmRegionUpsert(BaseModel):
    region_id: str
    name: str
    lat: float
    lon: float
    country_cca2: str
    geography: str
    kind: str
    status: REGION_STATUS = "ga"
    last_updated: Optional[str] = None


class IbmRegionBulkSync(BaseModel):
    regions: list[IbmRegionUpsert]


# ── Availability Zone (shared across all providers) ───────────────────────────

class AvailabilityZoneOut(BaseModel):
    az_id: str                  # "{provider}:{region_id}:{az_name}"
    provider: str               # "aws" | "azure" | "gcp" | "alibaba" | "oci" | "ibm"
    region_id: str
    az_name: str
    status: str = "ga"
    last_updated: Optional[str] = None


class AvailabilityZoneUpsert(BaseModel):
    provider: str
    region_id: str
    az_name: str
    status: REGION_STATUS = "ga"
    last_updated: Optional[str] = None


class AvailabilityZoneBulkSync(BaseModel):
    zones: list[AvailabilityZoneUpsert]


# ── Airline ───────────────────────────────────────────────────────────────────

class AirlineOut(BaseModel):
    iata: str
    icao: Optional[str] = None
    name: str
    country: Optional[str] = None          # ISO alpha-2
    alliance: Optional[str] = None
    hub: Optional[str] = None
    active: Optional[bool] = None          # populated by cron
    last_checked: Optional[str] = None     # ISO 8601 datetime, set by cron
    source: Optional[str] = None           # e.g. "opensky", "manual"


class AirlineUpsert(BaseModel):
    iata: str
    icao: Optional[str] = None
    name: str
    country: Optional[str] = None
    alliance: Optional[str] = None
    hub: Optional[str] = None
    active: Optional[bool] = None
    last_checked: Optional[str] = None
    source: Optional[str] = None


class AirlineBulkSync(BaseModel):
    airlines: list[AirlineUpsert]


# ── Globe Config ─────────────────────────────────────────────────────────────

class GlobeConfigCreate(BaseModel):
    name: str
    dot_color: str = "#4fc3f7"
    dot_size: float = Field(default=0.022, gt=0)
    rotation_speed: float = Field(default=0.12, ge=0)
    background_color: str = "#020a14"
    atmosphere_color: str = "#1a6dbf"


class GlobeConfigUpdate(BaseModel):
    name: Optional[str] = None
    dot_color: Optional[str] = None
    dot_size: Optional[float] = Field(default=None, gt=0)
    rotation_speed: Optional[float] = Field(default=None, ge=0)
    background_color: Optional[str] = None
    atmosphere_color: Optional[str] = None


class GlobeConfigOut(BaseModel):
    config_id: str
    name: str
    dot_color: str
    dot_size: float
    rotation_speed: float
    background_color: str
    atmosphere_color: str
