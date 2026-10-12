"""Assertions for the infrastructure claims made in FEDRAMP_GAP_ANALYSIS.md (SC-5/7/8).

Run: cd infra && pip install -r requirements.txt pytest && pytest tests
Uses a dummy account; no AWS access or context lookups are performed.
"""
import sys
from pathlib import Path

import pytest

pytest.importorskip("aws_cdk")
import aws_cdk as cdk  # noqa: E402
from aws_cdk.assertions import Match, Template  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mindmap_geo_lambda_stack import MindmapGeoLambdaStack  # noqa: E402

CERT = "arn:aws:acm:us-east-1:000000000000:certificate/00000000-0000-0000-0000-000000000000"


def _template(**context) -> Template:
    app = cdk.App(context={"allowed_ips": "203.0.113.10/32", **context})
    stack = MindmapGeoLambdaStack(
        app, "T", env=cdk.Environment(account="000000000000", region="us-east-1"),
    )
    return Template.from_stack(stack)


@pytest.fixture(scope="module")
def t() -> Template:
    return _template(cert_arn=CERT)


def test_all_buckets_private_and_not_websites(t):
    buckets = t.find_resources("AWS::S3::Bucket")
    assert len(buckets) == 2
    for res in buckets.values():
        p = res["Properties"]
        assert "WebsiteConfiguration" not in p
        assert p["PublicAccessBlockConfiguration"] == {
            "BlockPublicAcls": True, "BlockPublicPolicy": True,
            "IgnorePublicAcls": True, "RestrictPublicBuckets": True,
        }


def test_no_internet_path_from_vpc(t):
    t.resource_count_is("AWS::EC2::InternetGateway", 0)
    t.resource_count_is("AWS::EC2::NatGateway", 0)
    t.resource_count_is("AWS::EC2::FlowLog", 1)


def test_api_lambda_runs_in_vpc(t):
    fns = t.find_resources("AWS::Lambda::Function", {"Properties": {"PackageType": "Image"}})
    assert len(fns) == 1
    assert "VpcConfig" in next(iter(fns.values()))["Properties"]


def test_lambda_role_can_manage_vpc_enis(t):
    """Regression: a role passed to the function does not get the VPC policy automatically."""
    t.has_resource_properties("AWS::IAM::Role", {
        "RoleName": "pai-mindmap-geo-v2-lambda-role",
        "ManagedPolicyArns": Match.array_with([
            Match.object_like({"Fn::Join": Match.array_with([Match.array_with([
                Match.string_like_regexp("service-role/AWSLambdaVPCAccessExecutionRole"),
            ])])}),
        ]),
    })


def test_waf_attached_to_stage(t):
    t.resource_count_is("AWS::WAFv2::WebACL", 1)
    t.resource_count_is("AWS::WAFv2::WebACLAssociation", 1)
    t.has_resource_properties("AWS::WAFv2::WebACL", {
        "Scope": "REGIONAL",
        "Rules": Match.array_with([Match.object_like({"Name": "RateLimitPerIp"})]),
    })


def test_custom_domain_tls12_and_default_endpoint_disabled(t):
    t.has_resource_properties("AWS::ApiGateway::DomainName", {
        "DomainName": "exploror.labs.pasadena.ai", "SecurityPolicy": "TLS_1_2",
    })
    t.has_resource_properties("AWS::ApiGateway::RestApi", {"DisableExecuteApiEndpoint": True})


def test_without_cert_default_endpoint_stays_enabled_and_cors_empty():
    t = _template()
    t.resource_count_is("AWS::ApiGateway::DomainName", 0)
    t.has_resource_properties("AWS::ApiGateway::RestApi", {"DisableExecuteApiEndpoint": False})
    t.has_resource_properties("AWS::Lambda::Function", {
        "Environment": {"Variables": Match.object_like({"CORS_ORIGINS": "[]"})},
    })


def test_ip_allowlist_is_fail_closed():
    app = cdk.App()   # no allowed_ips context
    with pytest.raises(ValueError, match="allowed_ips"):
        MindmapGeoLambdaStack(app, "T", env=cdk.Environment(account="000000000000", region="us-east-1"))


def _deletion_policies(t: Template, typ: str) -> set:
    return {r.get("DeletionPolicy") for r in t.find_resources(typ).values()}


def test_data_is_retained_by_default():
    t = _template(cert_arn=CERT)
    # == (not >=): every table must be Retain, so a hard-coded DESTROY on one table fails here.
    assert _deletion_policies(t, "AWS::DynamoDB::Table") == {"Retain"}
    assert _deletion_policies(t, "AWS::SecretsManager::Secret") == {"Retain"}


def test_data_removal_destroy_deletes_data_but_never_the_secret():
    t = _template(cert_arn=CERT, data_removal="destroy")
    assert _deletion_policies(t, "AWS::DynamoDB::Table") == {"Delete"}
    assert "Retain" not in _deletion_policies(t, "AWS::Logs::LogGroup")
    assert _deletion_policies(t, "AWS::SecretsManager::Secret") == {"Retain"}


def test_static_header_mappings_have_no_escaped_quotes(t):
    """Regression: API Gateway emits `\\'` literally, which silently corrupts a CSP value."""
    for res in t.find_resources("AWS::ApiGateway::Method").values():
        for ir in res["Properties"]["Integration"].get("IntegrationResponses", []):
            for name, value in (ir.get("ResponseParameters") or {}).items():
                assert "\\" not in str(value), f"{name} contains a backslash: {value}"
                assert "Content-Security-Policy" not in name, "CSP must ship via <meta>, not a mapping"
