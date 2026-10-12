"""
mindmap-geo — Beta Lambda Deployment Stack
==========================================
Zero-NAT, zero-ALB, zero-Fargate, zero-CloudFront beta track.
FastAPI backend runs on Lambda via Mangum.
React frontend lives in a PRIVATE S3 bucket and is served through the same API Gateway
(S3 service integration), so the whole site is HTTPS on one origin:

  Browser --TLS 1.2+--> API Gateway (Regional custom domain + ACM cert, WAF)
     |- GET /, /{proxy+}   -> S3 service integration (private bucket, GetObject only)
     |- ANY /api/{proxy+}  -> Lambda (FastAPI/Mangum)
     '- GET /health        -> Lambda

CloudFront is deliberately not used: it is not offered inside the GovCloud partition, and every
construct here exists there too (partition-aware ARNs via self.partition).
Access restricted to allowed IP addresses (resource policy) plus WAF.

Estimated monthly cost: ~$18
  Lambda:          $0  (free tier: 1M req/month, 400K GB-seconds)
  API Gateway:     $0  (free tier: 1M calls/month for 12 months)
  WAF:            ~$8  (1 web ACL $5 + 3 rules $3 + $0.60/M requests)
  Secrets Mgr endpoint (1 AZ): ~$7.30
  S3 (frontend):  ~$0.05
  DynamoDB:       ~$1.00  (on-demand, low traffic; gateway endpoint is free)
  ECR:            ~$0.50  (1 image ~500MB)
  Flow logs:      ~$0-1
  ─────────────────────────
  Total:          ~$18/month

No NAT Gateway (the VPC Lambda has no internet egress). No ALB. No Fargate.
Upgrade to Fargate track (pai-aws01-infra) when ready for multi-user access.

Access restriction:
  API Gateway REST API resource policy — IP whitelist.
  Set allowed IPs via CDK context:
    cdk deploy MindmapGeoV2Stack --context allowed_ips=YOUR_IP/32
  Multiple IPs (comma-separated):
    cdk deploy MindmapGeoV2Stack --context allowed_ips=1.2.3.4/32,5.6.7.8/32

Prerequisites before deploying:
  1. Build + push backend image to ECR:
       aws ecr create-repository --repository-name pai-mindmap-geo-v2-backend
       cd backend
       docker buildx build --platform linux/arm64 --provenance=false \\
         -f Dockerfile.lambda \\
         -t <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/pai-mindmap-geo-v2-backend:latest \\
         --push .
  2. cdk bootstrap aws://<ACCOUNT_ID>/us-east-1  (one-time per account/region)
  3. Issue an ACM public cert (same account + region) for the site hostname, e.g.
     exploror.labs.pasadena.ai, validate it via DNS, and note its ARN.
  4. cdk deploy MindmapGeoV2Stack --context allowed_ips=YOUR.IP.HERE/32 \\
       --context cert_arn=<ACM cert ARN> [--context domain_name=exploror.labs.pasadena.ai]
     Without cert_arn the stack still deploys (default execute-api URL, HTTPS) but has no
     custom domain and CORS_ORIGINS is empty.

Post-deploy:
  5. DNS: CNAME (or alias) <domain_name> -> RegionalDomainName from the CDK outputs.
  6. Seed ingest sources via the API (runs _seed_ingest_sources on first ingest call)
     or trigger POST /api/geo/ingest/run/usgs_mcs to populate geo_ingest_sources.
  7. Build React frontend (same-origin: leave VITE_API_URL UNSET so the app calls /api):
       cd frontend && npm ci && npm run build
  8. Upload to S3 (the API Gateway role reads this private bucket). Only Vite's hashed
     assets/*.js|css are immutable; data files and flags keep stable paths, so they get a
     short TTL, and index.html is never cached:
       aws s3 sync frontend/dist s3://<FrontendBucketName> --delete --exclude "*.py" \\
         --cache-control "public,max-age=300"
       aws s3 cp frontend/dist s3://<FrontendBucketName> --recursive --exclude "*" \\
         --include "assets/*.js" --include "assets/*.css" \\
         --cache-control "public,max-age=31536000,immutable"
       aws s3 cp frontend/dist/index.html s3://<FrontendBucketName>/index.html \\
         --cache-control "no-cache" --content-type "text/html; charset=utf-8"
  9. Open FrontendUrl from CDK output in browser

Updating after code changes:
  Backend:
    docker buildx build --platform linux/arm64 --provenance=false \\
      -f backend/Dockerfile.lambda \\
      -t <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/pai-mindmap-geo-v2-backend:latest \\
      --push backend/
    aws lambda update-function-code \\
      --function-name pai-mindmap-geo-v2-backend \\
      --region us-east-1 \\
      --image-uri <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/pai-mindmap-geo-v2-backend:latest
    aws lambda wait function-updated --function-name pai-mindmap-geo-v2-backend --region us-east-1

  Frontend:
    cd frontend
    npm run build            # VITE_API_URL unset -> same-origin /api
    (then the three upload commands from step 8 above)

  Infrastructure:
    cd infra
    source .venv/bin/activate
    cdk deploy MindmapGeoV2Stack \\
      --app "python app.py" \\
      --context allowed_ips=YOUR.IP.HERE/32 \\
      --require-approval never
"""

import json

import aws_cdk as cdk
from aws_cdk import (
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_certificatemanager as acm,
    aws_dynamodb as dynamodb,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_logs as logs,
    aws_ecr as ecr,
    aws_s3 as s3,
    aws_secretsmanager as secretsmanager,
    aws_wafv2 as wafv2,
)
from constructs import Construct

SEVEN_YEARS = logs.RetentionDays.TEN_YEARS
TP = "v2_"  # table-name prefix: keeps these tables apart from the v1 stack
APP_SECRET_NAME = "pai-mindmap-geo-v2/app"
DEFAULT_DOMAIN = "exploror.labs.pasadena.ai"  # labs codename for mindmap-geo (domains_pasadenaai.md)

# Response headers added to every object served from S3 (API responses get their own set from
# the FastAPI middleware). Google Fonts is the only third-party origin the frontend loads.
# TODO: self-host Inter and drop fonts.googleapis.com / fonts.gstatic.com from the CSP.
CSP = (
    "default-src 'self'; script-src 'self'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' data: https://fonts.gstatic.com; "
    "img-src 'self' data: blob:; connect-src 'self'; worker-src 'self' blob:; "
    "base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)
SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": CSP,
}


def _static(value: str) -> str:
    """Quote a literal for an API Gateway response-parameter mapping expression."""
    return "'" + value.replace("'", "\\'") + "'"


class MindmapGeoLambdaStack(cdk.Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── Allowed IPs ───────────────────────────────────────────────────────
        # Pass via: cdk deploy --context allowed_ips=1.2.3.4/32
        # Multiple: --context allowed_ips=1.2.3.4/32,5.6.7.8/32
        # Find your IP: curl https://checkip.amazonaws.com
        allowed_ips_raw = self.node.try_get_context("allowed_ips")
        if not allowed_ips_raw:
            raise ValueError(
                "allowed_ips context is required (fail closed). "
                "Deploy with: --context allowed_ips=YOUR.IP.HERE/32"
            )
        allowed_ips = [ip.strip() for ip in allowed_ips_raw.split(",")]

        if "0.0.0.0/0" in allowed_ips:
            cdk.Annotations.of(self).add_warning(
                "allowed_ips includes 0.0.0.0/0 — API and frontend are open to the world."
            )

        # ── Site hostname + certificate ───────────────────────────────────────
        # --context cert_arn=<ACM cert in this account/region> enables the custom domain.
        # --context domain_name=... overrides the default labs hostname.
        # --context api_access_logs=true enables stage access logs (only valid if the
        #   account-level API Gateway CloudWatch role is already set; this stack never
        #   creates or repoints it — v1 owns it).
        domain_name = self.node.try_get_context("domain_name") or DEFAULT_DOMAIN
        cert_arn = self.node.try_get_context("cert_arn")
        access_logs_on = str(self.node.try_get_context("api_access_logs")).lower() == "true"
        # --context data_removal=destroy: for first-deploy / throwaway attempts only. Tables, log
        #   groups and the assets bucket are then deleted with the stack (a failed first create
        #   cleans itself up instead of leaving RETAINed orphans that block the next deploy).
        #   Default is RETAIN. The app secret is always RETAINed: Secrets Manager holds a deleted
        #   secret's name for 7-30 days, so DESTROY would block re-creating it.
        destroy_data = str(self.node.try_get_context("data_removal")).lower() == "destroy"
        data_removal = cdk.RemovalPolicy.DESTROY if destroy_data else cdk.RemovalPolicy.RETAIN
        if destroy_data:
            cdk.Annotations.of(self).add_warning(
                "data_removal=destroy: DynamoDB tables, log groups and the assets bucket will be "
                "DELETED with the stack. Do not use for a stack holding real data."
            )
        site_origins = [f"https://{domain_name}"] if cert_arn else []
        if not cert_arn:
            cdk.Annotations.of(self).add_warning(
                "cert_arn context not set — no custom domain; the site is only reachable on "
                "the default execute-api URL and CORS_ORIGINS is empty."
            )

        # ── DynamoDB Tables ───────────────────────────────────────────────────
        # All on-demand billing, PITR enabled, RemovalPolicy.RETAIN.
        # Tables match settings defaults in backend/app/core/config.py.
        # ensure_tables() is skipped in Lambda — CDK is the authoritative creator.

        def _table(logical_id: str, table_name: str, pk: str) -> dynamodb.Table:
            return dynamodb.Table(
                self, logical_id,
                table_name=table_name,
                partition_key=dynamodb.Attribute(
                    name=pk,
                    type=dynamodb.AttributeType.STRING,
                ),
                billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
                point_in_time_recovery=True,
                removal_policy=data_removal,
            )

        # Auth — users table with GSI on username
        geo_users_table = dynamodb.Table(
            self, "GeoUsersTable",
            table_name=f"{TP}geo_users",
            partition_key=dynamodb.Attribute(name="user_id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=data_removal,
        )
        geo_users_table.add_global_secondary_index(
            index_name="username-index",
            partition_key=dynamodb.Attribute(name="username", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # Core geo tables
        _table("GeoPointsTable",        f"{TP}geo_points",        "point_id")
        _table("GeoArcsTable",          f"{TP}geo_arcs",          "arc_id")
        _table("GeoConfigsTable",       f"{TP}geo_configs",       "config_id")
        _table("GeoCountriesTable",     f"{TP}geo_countries",     "cca2")

        # Cloud region tables
        _table("AwsRegionsTable",       f"{TP}aws_regions",       "region_id")
        _table("AzureRegionsTable",     f"{TP}azure_regions",     "region_id")
        _table("GcpRegionsTable",       f"{TP}gcp_regions",       "region_id")
        _table("AlibabaRegionsTable",   f"{TP}alibaba_regions",   "region_id")
        _table("OciRegionsTable",       f"{TP}oci_regions",       "region_id")
        _table("IbmRegionsTable",       f"{TP}ibm_regions",       "region_id")
        _table("GeoAvailabilityZonesTable", f"{TP}geo_availability_zones", "az_id")

        # Transport
        _table("GeoAirlinesTable",      f"{TP}geo_airlines",      "iata")

        # Elements & mineral reserves
        _table("GeoElementsTable",          f"{TP}geo_elements",          "atomic_number")
        _table("GeoCountryElementsTable",   f"{TP}geo_country_elements",  "cca2")
        _table("GeoCountryResourcesTable",  f"{TP}geo_country_resources", "cca2")

        # Ingest pipeline
        _table("GeoIngestSourcesTable", f"{TP}geo_ingest_sources", "source_id")
        _table("GeoIngestLogTable",     f"{TP}geo_ingest_log",     "run_id")

        # Hazard events & advisory alerts (docs/HAZARD_ALERTS_DESIGN.md)
        S = dynamodb.AttributeType.STRING

        # Raw normalized events — high churn; expire via TTL (epoch seconds in `ttl`).
        geo_events = dynamodb.Table(
            self, "GeoEventsTable",
            table_name=f"{TP}geo_events",
            partition_key=dynamodb.Attribute(name="event_id", type=S),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )
        geo_events.add_global_secondary_index(
            index_name="hazard-event_time-index",
            partition_key=dynamodb.Attribute(name="hazard", type=S),
            sort_key=dynamodb.Attribute(name="event_time", type=S),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # Live, visible alerts (7 days). No TTL: expired alerts are moved to the archive
        # table by a housekeeping job, never deleted.
        geo_alerts = dynamodb.Table(
            self, "GeoAlertsTable",
            table_name=f"{TP}geo_alerts",
            partition_key=dynamodb.Attribute(name="alert_id", type=S),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=data_removal,
        )
        geo_alerts.add_global_secondary_index(
            index_name="status-created-index",
            partition_key=dynamodb.Attribute(name="status", type=S),
            sort_key=dynamodb.Attribute(name="created_at", type=S),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # Archive: history for context, trends and forecasts.
        geo_alerts_archive = dynamodb.Table(
            self, "GeoAlertsArchiveTable",
            table_name=f"{TP}geo_alerts_archive",
            partition_key=dynamodb.Attribute(name="hazard", type=S),
            sort_key=dynamodb.Attribute(name="created_at_alert_id", type=S),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=data_removal,
        )
        geo_alerts_archive.add_global_secondary_index(
            index_name="cca2-created-index",
            partition_key=dynamodb.Attribute(name="primary_cca2", type=S),
            sort_key=dynamodb.Attribute(name="created_at", type=S),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # Daily per-country, per-hazard rollups for trends.
        dynamodb.Table(
            self, "GeoEventRollupsTable",
            table_name=f"{TP}geo_event_rollups",
            partition_key=dynamodb.Attribute(name="cca2", type=S),
            sort_key=dynamodb.Attribute(name="day_hazard", type=S),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=data_removal,
        )

        # ── App secret (Secrets Manager, KMS-encrypted at rest) ───────────────
        # SECRET_KEY (JWT signing) is generated by Secrets Manager and never seen by a human.
        # EIA_API_KEY starts empty — set it out-of-band:
        #   aws secretsmanager put-secret-value --secret-id pai-mindmap-geo-v2/app \\
        #     --secret-string '{"SECRET_KEY":"<existing>","EIA_API_KEY":"<value>"}'
        # (read the existing SECRET_KEY first so it is preserved.)
        app_secret = secretsmanager.Secret(
            self, "MindmapGeoAppSecret",
            secret_name=APP_SECRET_NAME,
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps({"EIA_API_KEY": ""}),
                generate_string_key="SECRET_KEY",
                password_length=64,
                exclude_punctuation=True,
            ),
            removal_policy=cdk.RemovalPolicy.RETAIN,   # always: see data_removal note above
        )

        # ── IAM Role for Lambda ───────────────────────────────────────────────
        lambda_role = iam.Role(
            self, "MindmapGeoLambdaRole",
            role_name="pai-mindmap-geo-v2-lambda-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )

        # CDK only attaches the VPC ENI permissions when it creates the role itself; this role
        # is passed in, so without this the function create fails with "execution role does not
        # have permissions to call CreateNetworkInterface".
        lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name(
            "service-role/AWSLambdaVPCAccessExecutionRole"
        ))

        # ── Inline policy 1: pai-mindmap-geo-v2-execution ────────────────────────
        # CloudWatch Logs + read of the single app secret (least privilege).
        lambda_role.attach_inline_policy(iam.Policy(
            self, "PaiMindmapGeoExecutionPolicy",
            policy_name="pai-mindmap-geo-v2-execution",
            statements=[
                iam.PolicyStatement(
                    sid="ReadAppSecret",
                    actions=["secretsmanager:GetSecretValue"],
                    resources=[app_secret.secret_arn],
                ),
                iam.PolicyStatement(
                    sid="CloudWatchLogs",
                    actions=[
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                    ],
                    resources=[
                        f"arn:{self.partition}:logs:*:*:log-group:/aws/lambda/pai-mindmap-geo-v2-*",
                        f"arn:{self.partition}:logs:*:*:log-group:/aws/lambda/pai-mindmap-geo-v2-*:*",
                    ],
                ),
            ],
        ))

        # ── Inline policy 2: pai-mindmap-geo-v2-data ────────────────────────────
        # DynamoDB access to all geo_* tables + cloud region tables + S3 geo assets.
        lambda_role.attach_inline_policy(iam.Policy(
            self, "PaiMindmapGeoDataPolicy",
            policy_name="pai-mindmap-geo-v2-data",
            statements=[
                iam.PolicyStatement(
                    sid="DynamoDBGeoTables",
                    actions=[
                        "dynamodb:BatchGetItem",
                        "dynamodb:BatchWriteItem",
                        "dynamodb:ConditionCheckItem",
                        "dynamodb:DeleteItem",
                        "dynamodb:DescribeTable",
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:Query",
                        "dynamodb:Scan",
                        "dynamodb:UpdateItem",
                    ],
                    # All tables of this stack (v2_ prefix)
                    resources=[
                        f"arn:{self.partition}:dynamodb:{self.region}:{self.account}:table/{TP}*",
                        f"arn:{self.partition}:dynamodb:{self.region}:{self.account}:table/{TP}*/index/*",
                    ],
                ),
                iam.PolicyStatement(
                    sid="S3GeoAssets",
                    actions=[
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:DeleteObject",
                        "s3:ListBucket",
                        "s3:HeadObject",
                    ],
                    resources=[
                        f"arn:{self.partition}:s3:::pai-mindmap-geo-v2-assets-{self.account}",
                        f"arn:{self.partition}:s3:::pai-mindmap-geo-v2-assets-{self.account}/*",
                    ],
                ),
            ],
        ))

        # ── CloudWatch Log Group ──────────────────────────────────────────────
        log_group = logs.LogGroup(
            self, "MindmapGeoLambdaLogs",
            log_group_name="/aws/lambda/pai-mindmap-geo-v2-backend",
            retention=SEVEN_YEARS,
            removal_policy=data_removal,
        )

        # ── Network: dedicated VPC, isolated subnets, endpoints only ──────────
        # The API Lambda runs in private-isolated subnets: no internet gateway, no NAT, so it
        # can reach only what has an endpoint here — DynamoDB (gateway, free) and Secrets
        # Manager (interface, one AZ to keep cost down; reachable from both AZs). Endpoint
        # policies pin each to this stack's own resources. Flow logs go to CloudWatch.
        # Consequence: anything needing the public internet (the /api/geo/ingest/run/* feeds:
        # EIA, USGS, hazard adapters) cannot run from this Lambda. See KNOWN_ISSUES.md.
        azs = [f"{self.region}a", f"{self.region}b"]
        vpc = ec2.Vpc(
            self, "MindmapGeoVpc",
            vpc_name="pai-mindmap-geo-v2-vpc",
            ip_addresses=ec2.IpAddresses.cidr("10.60.0.0/24"),
            availability_zones=azs,              # explicit: no context lookup at synth time
            nat_gateways=0,
            restrict_default_security_group=True,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="private",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=26,
                ),
            ],
        )

        lambda_sg = ec2.SecurityGroup(
            self, "ApiLambdaSg", vpc=vpc, allow_all_outbound=False,
            description="pai-mindmap-geo-v2 API Lambda: HTTPS egress only",
        )
        # 443 to anywhere is bounded by routing: the subnets have no route to the internet,
        # only to the endpoints below. (A prefix-list rule would need an account lookup.)
        lambda_sg.add_egress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(443), "HTTPS to VPC endpoints")
        endpoint_sg = ec2.SecurityGroup(
            self, "SecretsEndpointSg", vpc=vpc, allow_all_outbound=False,
            description="pai-mindmap-geo-v2 Secrets Manager endpoint: HTTPS from the API Lambda only",
        )
        endpoint_sg.add_ingress_rule(lambda_sg, ec2.Port.tcp(443), "API Lambda")

        ddb_endpoint = vpc.add_gateway_endpoint(
            "DynamoDbEndpoint", service=ec2.GatewayVpcEndpointAwsService.DYNAMODB,
        )
        ddb_endpoint.add_to_policy(iam.PolicyStatement(
            principals=[iam.AnyPrincipal()],
            actions=[
                "dynamodb:BatchGetItem", "dynamodb:BatchWriteItem", "dynamodb:ConditionCheckItem",
                "dynamodb:DeleteItem", "dynamodb:DescribeTable", "dynamodb:GetItem",
                "dynamodb:PutItem", "dynamodb:Query", "dynamodb:Scan", "dynamodb:UpdateItem",
            ],
            resources=[
                f"arn:{self.partition}:dynamodb:{self.region}:{self.account}:table/{TP}*",
                f"arn:{self.partition}:dynamodb:{self.region}:{self.account}:table/{TP}*/index/*",
            ],
        ))

        secrets_endpoint = vpc.add_interface_endpoint(
            "SecretsManagerEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED, availability_zones=[azs[0]],
            ),
            security_groups=[endpoint_sg],
            private_dns_enabled=True,
        )
        secrets_endpoint.add_to_policy(iam.PolicyStatement(
            principals=[iam.AnyPrincipal()],
            actions=["secretsmanager:GetSecretValue"],
            resources=[app_secret.secret_arn],
        ))

        flow_log_group = logs.LogGroup(
            self, "VpcFlowLogs",
            log_group_name="/aws/vpc/pai-mindmap-geo-v2-flow",
            retention=SEVEN_YEARS,
            removal_policy=data_removal,
        )
        vpc.add_flow_log(
            "FlowLogsAll",
            destination=ec2.FlowLogDestination.to_cloud_watch_logs(flow_log_group),
            traffic_type=ec2.FlowLogTrafficType.ALL,
        )

        # ── Lambda Function (FastAPI + Mangum) ────────────────────────────────
        # Container image from ECR. Build + push before deploying (see prerequisites).
        backend_repo = ecr.Repository.from_repository_name(
            self, "MindmapGeoBackendRepo",
            repository_name="pai-mindmap-geo-v2-backend",
        )

        backend_fn = lambda_.DockerImageFunction(
            self, "MindmapGeoBackendFn",
            function_name="pai-mindmap-geo-v2-backend",
            code=lambda_.DockerImageCode.from_ecr(
                repository=backend_repo,
                tag_or_digest="latest",
                cmd=["app.main.handler"],
            ),
            architecture=lambda_.Architecture.ARM_64,
            role=lambda_role,
            timeout=cdk.Duration.seconds(30),
            memory_size=512,
            environment={
                "APP_ENV": "aws",
                "SECRETS_BACKEND": "aws",
                "AWS_SECRET_NAME": APP_SECRET_NAME,
                "STORAGE_BACKEND": "dynamo",
                "AWS_REGION_NAME": self.region,
                # Table names match config.py defaults — explicit for clarity
                "DYNAMO_GEO_POINTS_TABLE":           f"{TP}geo_points",
                "DYNAMO_GEO_ARCS_TABLE":             f"{TP}geo_arcs",
                "DYNAMO_GEO_CONFIGS_TABLE":          f"{TP}geo_configs",
                "DYNAMO_GEO_COUNTRIES_TABLE":        f"{TP}geo_countries",
                "DYNAMO_AWS_REGIONS_TABLE":          f"{TP}aws_regions",
                "DYNAMO_AZURE_REGIONS_TABLE":        f"{TP}azure_regions",
                "DYNAMO_GCP_REGIONS_TABLE":          f"{TP}gcp_regions",
                "DYNAMO_ALIBABA_REGIONS_TABLE":      f"{TP}alibaba_regions",
                "DYNAMO_OCI_REGIONS_TABLE":          f"{TP}oci_regions",
                "DYNAMO_IBM_REGIONS_TABLE":          f"{TP}ibm_regions",
                "DYNAMO_AIRLINES_TABLE":             f"{TP}geo_airlines",
                "DYNAMO_AVAILABILITY_ZONES_TABLE":   f"{TP}geo_availability_zones",
                "DYNAMO_ELEMENTS_TABLE":             f"{TP}geo_elements",
                "DYNAMO_COUNTRY_ELEMENTS_TABLE":     f"{TP}geo_country_elements",
                "DYNAMO_COUNTRY_RESOURCES_TABLE":    f"{TP}geo_country_resources",
                "DYNAMO_INGEST_SOURCES_TABLE":       f"{TP}geo_ingest_sources",
                "DYNAMO_INGEST_LOG_TABLE":           f"{TP}geo_ingest_log",
                "DYNAMO_USERS_TABLE":                f"{TP}geo_users",
                "DYNAMO_EVENTS_TABLE":              f"{TP}geo_events",
                "DYNAMO_ALERTS_TABLE":              f"{TP}geo_alerts",
                "DYNAMO_ALERTS_ARCHIVE_TABLE":      f"{TP}geo_alerts_archive",
                "DYNAMO_EVENT_ROLLUPS_TABLE":       f"{TP}geo_event_rollups",
                "S3_GEO_BUCKET":                     f"pai-mindmap-geo-v2-assets-{self.account}",
                # Auth token expiry (short-lived in AWS)
                "ACCESS_TOKEN_EXPIRE_MINUTES":       "15",
                "REFRESH_TOKEN_EXPIRE_DAYS":         "1",
                # SECRET_KEY / EIA_API_KEY live in Secrets Manager (see app_secret above).
                # The site is served same-origin (API Gateway), so CORS only needs the site's own
                # origin; empty when no custom domain is configured.
                "CORS_ORIGINS": json.dumps(site_origins),
            },
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[lambda_sg],
            allow_public_subnet=False,
            log_group=log_group,
        )

        # ── S3 buckets (both PRIVATE) ─────────────────────────────────────────
        # No S3 website endpoint (it is HTTP-only and would fail SC-8). The frontend bucket is
        # read only by the API Gateway service-integration role defined below.
        assets_bucket = s3.Bucket(
            self, "MindmapGeoAssetsBucket",
            bucket_name=f"pai-mindmap-geo-v2-assets-{self.account}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=data_removal,
            auto_delete_objects=destroy_data,
        )

        frontend_bucket = s3.Bucket(
            self, "MindmapGeoFrontendBucket",
            bucket_name=f"pai-mindmap-geo-v2-frontend-{self.account}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=cdk.RemovalPolicy.DESTROY,   # rebuildable from `npm run build`
            auto_delete_objects=True,
        )

        # ── API Gateway REST API (site + API on one HTTPS origin) ─────────────
        # REST API (not HTTP API) — required for resource policy IP restriction and WAF.
        # The account-wide API Gateway CloudWatch role is owned by v1; v2 must not create or
        # repoint it (cloud_watch_role=False). Access logs are opt-in via api_access_logs.
        access_log_group = None
        if access_logs_on:
            access_log_group = logs.LogGroup(
                self, "ApiAccessLogs",
                log_group_name="/aws/apigateway/pai-mindmap-geo-v2-access",
                retention=SEVEN_YEARS,
                removal_policy=data_removal,
            )

        api = apigw.RestApi(
            self, "MindmapGeoApi",
            rest_api_name="pai-mindmap-geo-v2-api",
            description="mindmap-geo v2 — site + API over HTTPS, IP-restricted, WAF",
            cloud_watch_role=False,
            endpoint_types=[apigw.EndpointType.REGIONAL],
            # "*/*": API Gateway picks binary vs text from the FIRST Accept media type, so a
            # short allow-list corrupts PNGs for browsers that lead with image/avif or webp.
            # Mangum returns isBase64Encoded=false for text/JSON, so Lambda responses are
            # unaffected.
            binary_media_types=["*/*"],
            # With a custom domain, only that hostname serves traffic.
            disable_execute_api_endpoint=bool(cert_arn),
            # gzip text/binary responses (the three.js bundle is >1 MB uncompressed)
            min_compression_size=cdk.Size.bytes(1024),
            deploy_options=apigw.StageOptions(
                stage_name="beta",
                logging_level=apigw.MethodLoggingLevel.OFF,
                data_trace_enabled=False,
                metrics_enabled=True,
                # Sized for the SPA as well as the API: every asset (JS, JSON data, 500+ SVG
                # flags) passes through this stage. Backend protection is the WAF rate rule
                # scoped to /api/ plus Lambda concurrency (FEDRAMP_GAP_ANALYSIS.md P-5).
                throttling_rate_limit=200,
                throttling_burst_limit=400,
                access_log_destination=(
                    apigw.LogGroupLogDestination(access_log_group) if access_log_group else None
                ),
                access_log_format=(
                    apigw.AccessLogFormat.json_with_standard_fields(
                        caller=False, http_method=True, ip=True, protocol=True,
                        request_time=True, resource_path=True, response_length=True,
                        status=True, user=False,
                    ) if access_log_group else None
                ),
            ),
            policy=iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        principals=[iam.AnyPrincipal()],
                        actions=["execute-api:Invoke"],
                        resources=["execute-api:/*/*/*"],
                        conditions={
                            "IpAddress": {
                                "aws:SourceIp": allowed_ips,
                            }
                        },
                    ),
                    iam.PolicyStatement(
                        effect=iam.Effect.DENY,
                        principals=[iam.AnyPrincipal()],
                        actions=["execute-api:Invoke"],
                        resources=["execute-api:/*/*/*"],
                        conditions={
                            "NotIpAddress": {
                                "aws:SourceIp": allowed_ips,
                            }
                        },
                    ),
                ]
            ),
        )

        # ── Lambda routes: /api/* and /health only ────────────────────────────
        backend_integration = apigw.LambdaIntegration(
            backend_fn,
            proxy=True,
            allow_test_invoke=False,
        )
        api.root.add_resource("api").add_resource("{proxy+}").add_method("ANY", backend_integration)
        api.root.add_resource("health").add_method("GET", backend_integration)

        # ── Static site routes: everything else → private S3 ──────────────────
        s3_read_role = iam.Role(
            self, "ApiS3ReadRole",
            role_name="pai-mindmap-geo-v2-apigw-s3-read",
            assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
        )
        s3_read_role.add_to_policy(iam.PolicyStatement(
            sid="ReadFrontendObjects",
            actions=["s3:GetObject"],
            resources=[frontend_bucket.arn_for_objects("*")],
        ))

        passthrough = {
            "Content-Type": "integration.response.header.Content-Type",
            "ETag": "integration.response.header.ETag",
            "Last-Modified": "integration.response.header.Last-Modified",
            "Cache-Control": "integration.response.header.Cache-Control",
        }
        sec_headers = {f"method.response.header.{h}": _static(v) for h, v in SECURITY_HEADERS.items()}
        ok_params = {f"method.response.header.{h}": m for h, m in passthrough.items()}
        ok_params.update(sec_headers)

        def _s3_integration(object_path: str, key_from_proxy: bool) -> apigw.AwsIntegration:
            return apigw.AwsIntegration(
                service="s3",
                integration_http_method="GET",
                path=f"{frontend_bucket.bucket_name}/{object_path}",
                options=apigw.IntegrationOptions(
                    credentials_role=s3_read_role,
                    request_parameters=(
                        {"integration.request.path.key": "method.request.path.proxy"}
                        if key_from_proxy else None
                    ),
                    integration_responses=[
                        apigw.IntegrationResponse(status_code="200", response_parameters=ok_params),
                        # S3 answers 403 (no ListBucket) or 404 for a missing key.
                        apigw.IntegrationResponse(
                            status_code="404", selection_pattern="4\\d{2}",
                            response_parameters=sec_headers),
                        apigw.IntegrationResponse(
                            status_code="502", selection_pattern="5\\d{2}",
                            response_parameters=sec_headers),
                    ],
                ),
            )

        def _s3_method_responses() -> list:
            return [
                apigw.MethodResponse(
                    status_code="200",
                    response_parameters={k: True for k in ok_params},
                ),
                apigw.MethodResponse(
                    status_code="404",
                    response_parameters={k: True for k in sec_headers},
                ),
                apigw.MethodResponse(
                    status_code="502",
                    response_parameters={k: True for k in sec_headers},
                ),
            ]

        api.root.add_method(
            "GET", _s3_integration("index.html", key_from_proxy=False),
            method_responses=_s3_method_responses(),
        )
        api.root.add_resource("{proxy+}").add_method(
            "GET", _s3_integration("{key}", key_from_proxy=True),
            request_parameters={"method.request.path.proxy": True},
            method_responses=_s3_method_responses(),
        )

        # ── WAF (regional) on the stage ───────────────────────────────────────
        def _vis(metric: str) -> wafv2.CfnWebACL.VisibilityConfigProperty:
            return wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name=metric,
                sampled_requests_enabled=True,
            )

        def _managed(name: str, priority: int, overrides=None) -> wafv2.CfnWebACL.RuleProperty:
            return wafv2.CfnWebACL.RuleProperty(
                name=name,
                priority=priority,
                override_action=wafv2.CfnWebACL.OverrideActionProperty(none={}),
                statement=wafv2.CfnWebACL.StatementProperty(
                    managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                        vendor_name="AWS",
                        name=name,
                        rule_action_overrides=overrides,
                    ),
                ),
                visibility_config=_vis(name),
            )

        web_acl = wafv2.CfnWebACL(
            self, "SiteWebAcl",
            name="pai-mindmap-geo-v2-waf",
            scope="REGIONAL",
            default_action=wafv2.CfnWebACL.DefaultActionProperty(allow={}),
            visibility_config=_vis("pai-mindmap-geo-v2-waf"),
            rules=[
                # SizeRestrictions_BODY is counted, not blocked: bulk /sync endpoints post
                # bodies larger than the 8 KB default.
                _managed("AWSManagedRulesCommonRuleSet", 1, overrides=[
                    wafv2.CfnWebACL.RuleActionOverrideProperty(
                        name="SizeRestrictions_BODY",
                        action_to_use=wafv2.CfnWebACL.RuleActionProperty(count={}),
                    ),
                ]),
                _managed("AWSManagedRulesKnownBadInputsRuleSet", 2),
                wafv2.CfnWebACL.RuleProperty(
                    name="RateLimitPerIp",
                    priority=3,
                    action=wafv2.CfnWebACL.RuleActionProperty(block={}),
                    statement=wafv2.CfnWebACL.StatementProperty(
                        rate_based_statement=wafv2.CfnWebACL.RateBasedStatementProperty(
                            limit=1000,              # requests per 5 minutes per source IP
                            aggregate_key_type="IP",
                            # Count only API calls: the SPA fetches hundreds of static files
                            # (one SVG flag per country) which must not trip the limit.
                            scope_down_statement=wafv2.CfnWebACL.StatementProperty(
                                byte_match_statement=wafv2.CfnWebACL.ByteMatchStatementProperty(
                                    search_string="/api/",
                                    field_to_match=wafv2.CfnWebACL.FieldToMatchProperty(
                                        uri_path={},
                                    ),
                                    positional_constraint="STARTS_WITH",
                                    text_transformations=[
                                        wafv2.CfnWebACL.TextTransformationProperty(
                                            priority=0, type="NONE",
                                        ),
                                    ],
                                ),
                            ),
                        ),
                    ),
                    visibility_config=_vis("RateLimitPerIp"),
                ),
            ],
        )
        web_acl_assoc = wafv2.CfnWebACLAssociation(
            self, "SiteWebAclAssociation",
            resource_arn=(
                f"arn:{self.partition}:apigateway:{self.region}::"
                f"/restapis/{api.rest_api_id}/stages/{api.deployment_stage.stage_name}"
            ),
            web_acl_arn=web_acl.attr_arn,
        )
        web_acl_assoc.node.add_dependency(api.deployment_stage)

        # ── Custom domain (Regional, ACM cert, TLS 1.2+) ──────────────────────
        # The hosted zone lives in a different AWS account, so DNS is NOT managed here:
        # point <domain_name> at RegionalDomainName with a CNAME in that account.
        site_url = api.url
        if cert_arn:
            site_domain = apigw.DomainName(
                self, "SiteDomain",
                domain_name=domain_name,
                certificate=acm.Certificate.from_certificate_arn(self, "SiteCert", cert_arn),
                endpoint_type=apigw.EndpointType.REGIONAL,
                security_policy=apigw.SecurityPolicy.TLS_1_2,
                mapping=api,
            )
            site_url = f"https://{domain_name}/"
            cdk.CfnOutput(
                self, "RegionalDomainName",
                value=site_domain.domain_name_alias_domain_name,
                description=f"Create a CNAME {domain_name} -> this value in the DNS account",
            )

        # ── Outputs ───────────────────────────────────────────────────────────
        cdk.CfnOutput(
            self, "FrontendUrl",
            value=site_url,
            description="Site URL (custom domain when cert_arn is set, otherwise execute-api)",
        )
        cdk.CfnOutput(
            self, "ApiGatewayUrl",
            value=api.url,
            description="Default execute-api URL (disabled when a custom domain is configured)",
        )
        cdk.CfnOutput(
            self, "FrontendBucketName",
            value=frontend_bucket.bucket_name,
            description="Private S3 bucket — upload the React build output here",
        )
        cdk.CfnOutput(
            self, "AssetsBucketName",
            value=assets_bucket.bucket_name,
            description="Private S3 bucket for geo static assets",
        )
        cdk.CfnOutput(
            self, "AllowedIps",
            value=", ".join(allowed_ips),
            description="IP addresses allowed to access the API and frontend",
        )
