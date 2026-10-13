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


def _image_fn(t, name):
    fns = t.find_resources("AWS::Lambda::Function", {"Properties": {"FunctionName": name}})
    assert len(fns) == 1, name
    return next(iter(fns.values()))["Properties"]


def test_api_lambda_runs_in_vpc(t):
    assert "VpcConfig" in _image_fn(t, "pai-mindmap-geo-v2-backend")


def test_only_two_image_functions_and_only_the_assistant_is_outside_the_vpc(t):
    """The no-egress boundary stays intact: exactly one function (the assistant) is outside the VPC."""
    fns = t.find_resources("AWS::Lambda::Function", {"Properties": {"PackageType": "Image"}})
    outside = [r["Properties"]["FunctionName"] for r in fns.values() if "VpcConfig" not in r["Properties"]]
    assert outside == ["pai-mindmap-geo-v2-assistant"]
    assert _image_fn(t, "pai-mindmap-geo-v2-assistant")["ImageConfig"]["Command"] == ["app.assistant_main.handler"]


def test_assistant_function_has_a_full_vcpu(t):
    """Cold-start regression: at 512 MB init exceeded Lambda's 10 s limit on every cold start."""
    assert _image_fn(t, "pai-mindmap-geo-v2-assistant")["MemorySize"] >= 1769


def _assistant_policy_statements(t):
    out = []
    for res in t.find_resources("AWS::IAM::Policy").values():
        if res["Properties"]["PolicyName"] == "pai-mindmap-geo-v2-assistant":
            out = res["Properties"]["PolicyDocument"]["Statement"]
    assert out, "assistant policy not found"
    return out


def test_assistant_role_is_read_only_and_scoped(t):
    """The assistant can read the secret and the countries table and nothing else (no writes, no S3, no wildcards)."""
    stmts = _assistant_policy_statements(t)
    actions = {a for st in stmts for a in (st["Action"] if isinstance(st["Action"], list) else [st["Action"]])}
    assert actions == {
        "secretsmanager:GetSecretValue",
        "dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan", "dynamodb:DescribeTable",
        "logs:CreateLogStream", "logs:PutLogEvents",
    }
    ddb = next(st for st in stmts if st.get("Sid") == "ReadCountriesTableOnly")
    assert "geo_countries" in str(ddb["Resource"]) and "*" not in str(ddb["Resource"]).replace("::", "")
    assert not any(st["Resource"] == "*" for st in stmts)


def test_assistant_route_is_post_only_with_its_own_throttle(t):
    resources = t.find_resources("AWS::ApiGateway::Resource", {"Properties": {"PathPart": "assistant"}})
    assert len(resources) == 1
    methods = t.find_resources("AWS::ApiGateway::Method", {"Properties": {"HttpMethod": "POST"}})
    assert any("Assistant" in str(m["Properties"]["Integration"]["Uri"]) for m in methods.values())
    t.has_resource_properties("AWS::ApiGateway::Stage", {
        "MethodSettings": Match.array_with([Match.object_like({
            "ResourcePath": "/~1api~1assistant", "HttpMethod": "POST",
            "ThrottlingRateLimit": 2, "ThrottlingBurstLimit": 5,
        })]),
    })


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


# ── Boundary assertions (SC-7): the S3 role, IP allowlist, WAF scope and Lambda egress ──────────

ALLOWED = ["203.0.113.10/32"]   # matches the allowed_ips context set in _template()


def _statements(doc) -> list:
    stmts = doc["Statement"]
    return stmts if isinstance(stmts, list) else [stmts]


def test_apigw_s3_role_can_only_get_objects_from_the_frontend_bucket(t):
    roles = t.find_resources("AWS::IAM::Role", {"Properties": {"RoleName": "pai-mindmap-geo-v2-apigw-s3-read"}})
    assert len(roles) == 1
    role_id = next(iter(roles))
    attached = [
        p["Properties"]["PolicyDocument"]
        for p in t.find_resources("AWS::IAM::Policy").values()
        if {"Ref": role_id} in p["Properties"].get("Roles", [])
    ]
    assert attached, "the S3 read role has no policy"
    stmts = [s for doc in attached for s in _statements(doc)]
    assert len(stmts) == 1
    assert stmts[0]["Effect"] == "Allow"
    assert stmts[0]["Action"] == "s3:GetObject"      # a bare string: exactly one action
    resource = str(stmts[0]["Resource"])
    assert "MindmapGeoFrontendBucket" in resource and "MindmapGeoAssetsBucket" not in resource


def test_ip_allowlist_allows_only_and_denies_everything_else(t):
    (api,) = t.find_resources("AWS::ApiGateway::RestApi").values()
    stmts = _statements(api["Properties"]["Policy"])
    allow = [s for s in stmts if s["Effect"] == "Allow"]
    deny = [s for s in stmts if s["Effect"] == "Deny"]
    assert len(allow) == 1 and len(deny) == 1
    assert allow[0]["Condition"] == {"IpAddress": {"aws:SourceIp": ALLOWED}}
    assert deny[0]["Condition"] == {"NotIpAddress": {"aws:SourceIp": ALLOWED}}
    for s in (allow[0], deny[0]):
        assert s["Action"] == "execute-api:Invoke"


def test_waf_rate_rule_counts_only_api_paths(t):
    (acl,) = t.find_resources("AWS::WAFv2::WebACL").values()
    (rule,) = [r for r in acl["Properties"]["Rules"] if r["Name"] == "RateLimitPerIp"]
    assert rule["Action"] == {"Block": {}}
    stmt = rule["Statement"]["RateBasedStatement"]
    assert stmt["AggregateKeyType"] == "IP" and stmt["Limit"] == 1000
    match = stmt["ScopeDownStatement"]["ByteMatchStatement"]
    assert match["SearchString"] == "/api/"
    assert match["PositionalConstraint"] == "STARTS_WITH"
    assert match["FieldToMatch"] == {"UriPath": {}}


def test_api_lambda_security_group_egress_is_https_only(t):
    groups = t.find_resources(
        "AWS::EC2::SecurityGroup",
        {"Properties": {"GroupDescription": Match.string_like_regexp("API Lambda: HTTPS egress only")}},
    )
    assert len(groups) == 1
    egress = next(iter(groups.values()))["Properties"]["SecurityGroupEgress"]
    assert egress, "no egress rules"
    for rule in egress:
        assert rule["IpProtocol"] == "tcp"
        assert rule["FromPort"] == 443 and rule["ToPort"] == 443
