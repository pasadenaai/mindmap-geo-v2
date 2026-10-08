from __future__ import annotations
import json
import logging
import secrets
from functools import lru_cache
from typing import Literal, Optional
from pydantic_settings import BaseSettings
from pydantic import Field

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    app_env: Literal["local", "aws"] = Field("local", alias="APP_ENV")
    secrets_backend: Literal["env", "aws"] = Field("env", alias="SECRETS_BACKEND")
    storage_backend: Literal["dynamo"] = Field("dynamo", alias="STORAGE_BACKEND")

    # JWT signing key. No default: local dev gets an ephemeral random key (see
    # get_settings); AWS must supply one via Secrets Manager or the environment.
    secret_key: Optional[str] = Field(None, alias="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(480, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # DynamoDB
    dynamodb_endpoint_url: Optional[str] = Field(None, alias="DYNAMODB_ENDPOINT_URL")
    aws_region: str = Field("us-east-1", alias="AWS_REGION")
    dynamo_users_table: str = Field("geo_users", alias="DYNAMO_USERS_TABLE")
    dynamo_geo_points_table: str = Field("geo_points", alias="DYNAMO_GEO_POINTS_TABLE")
    dynamo_geo_arcs_table: str = Field("geo_arcs", alias="DYNAMO_GEO_ARCS_TABLE")
    dynamo_geo_configs_table: str = Field("geo_configs", alias="DYNAMO_GEO_CONFIGS_TABLE")
    dynamo_geo_countries_table: str = Field("geo_countries", alias="DYNAMO_GEO_COUNTRIES_TABLE")
    dynamo_aws_regions_table: str = Field("aws_regions", alias="DYNAMO_AWS_REGIONS_TABLE")
    dynamo_azure_regions_table: str = Field("azure_regions", alias="DYNAMO_AZURE_REGIONS_TABLE")
    dynamo_gcp_regions_table: str = Field("gcp_regions", alias="DYNAMO_GCP_REGIONS_TABLE")
    dynamo_alibaba_regions_table: str = Field("alibaba_regions", alias="DYNAMO_ALIBABA_REGIONS_TABLE")
    dynamo_oci_regions_table: str = Field("oci_regions", alias="DYNAMO_OCI_REGIONS_TABLE")
    dynamo_ibm_regions_table: str = Field("ibm_regions", alias="DYNAMO_IBM_REGIONS_TABLE")
    dynamo_airlines_table: str = Field("geo_airlines", alias="DYNAMO_AIRLINES_TABLE")
    dynamo_availability_zones_table: str = Field("geo_availability_zones", alias="DYNAMO_AVAILABILITY_ZONES_TABLE")
    dynamo_elements_table: str = Field("geo_elements", alias="DYNAMO_ELEMENTS_TABLE")
    dynamo_country_elements_table: str = Field("geo_country_elements", alias="DYNAMO_COUNTRY_ELEMENTS_TABLE")
    dynamo_country_resources_table: str = Field("geo_country_resources", alias="DYNAMO_COUNTRY_RESOURCES_TABLE")
    dynamo_ingest_sources_table: str = Field("geo_ingest_sources", alias="DYNAMO_INGEST_SOURCES_TABLE")
    dynamo_ingest_log_table: str = Field("geo_ingest_log", alias="DYNAMO_INGEST_LOG_TABLE")

    # External data source API keys
    eia_api_key: Optional[str] = Field(None, alias="EIA_API_KEY")

    # S3
    s3_endpoint_url: Optional[str] = Field(None, alias="S3_ENDPOINT_URL")
    s3_public_endpoint_url: Optional[str] = Field(None, alias="S3_PUBLIC_ENDPOINT_URL")
    s3_geo_bucket: str = Field("geo-assets-local", alias="S3_GEO_BUCKET")

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:4203"],
        alias="CORS_ORIGINS",
    )

    # AWS Secrets Manager
    aws_secret_name: str = Field("pai-mindmap-geo/app", alias="AWS_SECRET_NAME")

    class Config:
        env_file = ".env"
        populate_by_name = True


def _load_aws_secret(name: str, region: str) -> dict:
    """Fetch the app secret (JSON object: SECRET_KEY, EIA_API_KEY) from Secrets Manager."""
    import boto3  # imported lazily; only needed when SECRETS_BACKEND=aws

    client = boto3.client("secretsmanager", region_name=region)
    return json.loads(client.get_secret_value(SecretId=name)["SecretString"])


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    s = Settings()
    if s.secrets_backend == "aws":
        values = _load_aws_secret(s.aws_secret_name, s.aws_region)
        s.secret_key = values.get("SECRET_KEY") or s.secret_key
        s.eia_api_key = values.get("EIA_API_KEY") or s.eia_api_key
    if not s.secret_key:
        if s.app_env == "aws":
            raise RuntimeError("SECRET_KEY is not configured (set it in Secrets Manager)")
        # Local dev: ephemeral key; tokens are invalidated on restart.
        logger.warning("SECRET_KEY not set; using an ephemeral random key for this process")
        s.secret_key = secrets.token_urlsafe(48)
    return s


settings: Settings = get_settings()
