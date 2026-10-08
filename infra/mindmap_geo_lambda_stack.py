"""
mindmap-geo — Beta Lambda Deployment Stack
==========================================
Zero-NAT, zero-ALB, zero-Fargate beta track.
FastAPI backend runs on Lambda via Mangum.
React frontend served from S3.
Access restricted to allowed IP addresses only.

Estimated monthly cost: ~$2
  Lambda:          $0  (free tier: 1M req/month, 400K GB-seconds)
  API Gateway:     $0  (free tier: 1M calls/month for 12 months)
  S3 (frontend):  ~$0.05
  DynamoDB:       ~$1.00  (17 tables, on-demand, low traffic)
  ECR:            ~$0.50  (1 image ~500MB)
  ─────────────────────────
  Total:          ~$2/month

No NAT Gateway. No ALB. No Fargate.
Upgrade to Fargate track (pai-aws01-infra) when ready for multi-user access.

Access restriction:
  API Gateway REST API resource policy — IP whitelist.
  Set allowed IPs via CDK context:
    cdk deploy MindmapGeoLambdaStack --context allowed_ips=YOUR_IP/32
  Multiple IPs (comma-separated):
    cdk deploy MindmapGeoLambdaStack --context allowed_ips=1.2.3.4/32,5.6.7.8/32

Prerequisites before deploying:
  1. Build + push backend image to ECR:
       aws ecr create-repository --repository-name pai-mindmap-geo-backend
       cd backend
       docker buildx build --platform linux/arm64 --provenance=false \\
         -f Dockerfile.lambda \\
         -t <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/pai-mindmap-geo-backend:latest \\
         --push .
  2. cdk bootstrap aws://<ACCOUNT_ID>/us-east-1  (one-time per account/region)
  3. cdk deploy MindmapGeoLambdaStack --context allowed_ips=YOUR.IP.HERE/32

Post-deploy:
  4. Seed ingest sources via the API (runs _seed_ingest_sources on first ingest call)
     or trigger POST /api/geo/ingest/run/usgs_mcs to populate geo_ingest_sources.
  5. Build React frontend:
       cd frontend && npm ci && VITE_API_URL=<ApiGatewayUrl from CDK output> npm run build
  6. Upload to S3:
       aws s3 sync frontend/dist s3://<FrontendBucketName from CDK output> --delete
  7. Open FrontendUrl from CDK output in browser

Updating after code changes:
  Backend:
    docker buildx build --platform linux/arm64 --provenance=false \\
      -f backend/Dockerfile.lambda \\
      -t <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/pai-mindmap-geo-backend:latest \\
      --push backend/
    aws lambda update-function-code \\
      --function-name pai-mindmap-geo-backend \\
      --region us-east-1 \\
      --image-uri <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/pai-mindmap-geo-backend:latest
    aws lambda wait function-updated --function-name pai-mindmap-geo-backend --region us-east-1

  Frontend:
    cd frontend
    VITE_API_URL=<ApiGatewayUrl> npm run build
    aws s3 sync dist s3://<FrontendBucketName> --delete

  Infrastructure:
    cd infra
    source .venv/bin/activate
    cdk deploy MindmapGeoLambdaStack \\
      --app "python app.py" \\
      --context allowed_ips=YOUR.IP.HERE/32 \\
      --require-approval never
"""

import json

import aws_cdk as cdk
from aws_cdk import (
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_logs as logs,
    aws_ecr as ecr,
    aws_s3 as s3,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct

SEVEN_YEARS = logs.RetentionDays.TEN_YEARS
APP_SECRET_NAME = "pai-mindmap-geo/app"


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
                removal_policy=cdk.RemovalPolicy.RETAIN,
            )

        # Auth — users table with GSI on username
        geo_users_table = dynamodb.Table(
            self, "GeoUsersTable",
            table_name="geo_users",
            partition_key=dynamodb.Attribute(name="user_id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=cdk.RemovalPolicy.RETAIN,
        )
        geo_users_table.add_global_secondary_index(
            index_name="username-index",
            partition_key=dynamodb.Attribute(name="username", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # Core geo tables
        _table("GeoPointsTable",        "geo_points",        "point_id")
        _table("GeoArcsTable",          "geo_arcs",          "arc_id")
        _table("GeoConfigsTable",       "geo_configs",       "config_id")
        _table("GeoCountriesTable",     "geo_countries",     "cca2")

        # Cloud region tables
        _table("AwsRegionsTable",       "aws_regions",       "region_id")
        _table("AzureRegionsTable",     "azure_regions",     "region_id")
        _table("GcpRegionsTable",       "gcp_regions",       "region_id")
        _table("AlibabaRegionsTable",   "alibaba_regions",   "region_id")
        _table("OciRegionsTable",       "oci_regions",       "region_id")
        _table("IbmRegionsTable",       "ibm_regions",       "region_id")
        _table("GeoAvailabilityZonesTable", "geo_availability_zones", "az_id")

        # Transport
        _table("GeoAirlinesTable",      "geo_airlines",      "iata")

        # Elements & mineral reserves
        _table("GeoElementsTable",          "geo_elements",          "atomic_number")
        _table("GeoCountryElementsTable",   "geo_country_elements",  "cca2")
        _table("GeoCountryResourcesTable",  "geo_country_resources", "cca2")

        # Ingest pipeline
        _table("GeoIngestSourcesTable", "geo_ingest_sources", "source_id")
        _table("GeoIngestLogTable",     "geo_ingest_log",     "run_id")

        # ── App secret (Secrets Manager, KMS-encrypted at rest) ───────────────
        # SECRET_KEY (JWT signing) is generated by Secrets Manager and never seen by a human.
        # EIA_API_KEY starts empty — set it out-of-band:
        #   aws secretsmanager put-secret-value --secret-id pai-mindmap-geo/app \\
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
            removal_policy=cdk.RemovalPolicy.RETAIN,
        )

        # ── IAM Role for Lambda ───────────────────────────────────────────────
        lambda_role = iam.Role(
            self, "MindmapGeoLambdaRole",
            role_name="pai-mindmap-geo-lambda-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )

        # ── Inline policy 1: pai-mindmap-geo-execution ────────────────────────
        # CloudWatch Logs + read of the single app secret (least privilege).
        lambda_role.attach_inline_policy(iam.Policy(
            self, "PaiMindmapGeoExecutionPolicy",
            policy_name="pai-mindmap-geo-execution",
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
                        "arn:aws:logs:*:*:log-group:/aws/lambda/pai-mindmap-geo-*",
                        "arn:aws:logs:*:*:log-group:/aws/lambda/pai-mindmap-geo-*:*",
                    ],
                ),
            ],
        ))

        # ── Inline policy 2: pai-mindmap-geo-data ────────────────────────────
        # DynamoDB access to all geo_* tables + cloud region tables + S3 geo assets.
        lambda_role.attach_inline_policy(iam.Policy(
            self, "PaiMindmapGeoDataPolicy",
            policy_name="pai-mindmap-geo-data",
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
                    # Covers all geo_* tables and cloud provider region tables
                    resources=[
                        "arn:aws:dynamodb:*:*:table/geo_*",
                        "arn:aws:dynamodb:*:*:table/geo_*/index/*",
                        "arn:aws:dynamodb:*:*:table/aws_regions",
                        "arn:aws:dynamodb:*:*:table/azure_regions",
                        "arn:aws:dynamodb:*:*:table/gcp_regions",
                        "arn:aws:dynamodb:*:*:table/alibaba_regions",
                        "arn:aws:dynamodb:*:*:table/oci_regions",
                        "arn:aws:dynamodb:*:*:table/ibm_regions",
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
                        f"arn:aws:s3:::pai-mindmap-geo-assets-{self.account}",
                        f"arn:aws:s3:::pai-mindmap-geo-assets-{self.account}/*",
                    ],
                ),
            ],
        ))

        # ── CloudWatch Log Group ──────────────────────────────────────────────
        log_group = logs.LogGroup(
            self, "MindmapGeoLambdaLogs",
            log_group_name="/aws/lambda/pai-mindmap-geo-backend",
            retention=SEVEN_YEARS,
            removal_policy=cdk.RemovalPolicy.RETAIN,
        )

        # ── Lambda Function (FastAPI + Mangum) ────────────────────────────────
        # Container image from ECR. Build + push before deploying (see prerequisites).
        backend_repo = ecr.Repository.from_repository_name(
            self, "MindmapGeoBackendRepo",
            repository_name="pai-mindmap-geo-backend",
        )

        backend_fn = lambda_.DockerImageFunction(
            self, "MindmapGeoBackendFn",
            function_name="pai-mindmap-geo-backend",
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
                "AWS_REGION_NAME": "us-east-1",
                # Table names match config.py defaults — explicit for clarity
                "DYNAMO_GEO_POINTS_TABLE":           "geo_points",
                "DYNAMO_GEO_ARCS_TABLE":             "geo_arcs",
                "DYNAMO_GEO_CONFIGS_TABLE":          "geo_configs",
                "DYNAMO_GEO_COUNTRIES_TABLE":        "geo_countries",
                "DYNAMO_AWS_REGIONS_TABLE":          "aws_regions",
                "DYNAMO_AZURE_REGIONS_TABLE":        "azure_regions",
                "DYNAMO_GCP_REGIONS_TABLE":          "gcp_regions",
                "DYNAMO_ALIBABA_REGIONS_TABLE":      "alibaba_regions",
                "DYNAMO_OCI_REGIONS_TABLE":          "oci_regions",
                "DYNAMO_IBM_REGIONS_TABLE":          "ibm_regions",
                "DYNAMO_AIRLINES_TABLE":             "geo_airlines",
                "DYNAMO_AVAILABILITY_ZONES_TABLE":   "geo_availability_zones",
                "DYNAMO_ELEMENTS_TABLE":             "geo_elements",
                "DYNAMO_COUNTRY_ELEMENTS_TABLE":     "geo_country_elements",
                "DYNAMO_COUNTRY_RESOURCES_TABLE":    "geo_country_resources",
                "DYNAMO_INGEST_SOURCES_TABLE":       "geo_ingest_sources",
                "DYNAMO_INGEST_LOG_TABLE":           "geo_ingest_log",
                "DYNAMO_USERS_TABLE":                "geo_users",
                "S3_GEO_BUCKET":                     f"pai-mindmap-geo-assets-{self.account}",
                # Auth token expiry (short-lived in AWS)
                "ACCESS_TOKEN_EXPIRE_MINUTES":       "15",
                "REFRESH_TOKEN_EXPIRE_DAYS":         "1",
                # SECRET_KEY / EIA_API_KEY live in Secrets Manager (see app_secret above).
                # CORS_ORIGINS — S3 frontend bucket URL
                "CORS_ORIGINS": f'["http://pai-mindmap-geo-frontend-{self.account}.s3-website-us-east-1.amazonaws.com"]',
            },
            log_group=log_group,
        )

        # ── API Gateway REST API ──────────────────────────────────────────────
        # REST API (not HTTP API) — required for resource policy IP restriction.
        api = apigw.RestApi(
            self, "MindmapGeoApi",
            rest_api_name="pai-mindmap-geo-api",
            description="mindmap-geo API — beta, IP-restricted",
            deploy_options=apigw.StageOptions(
                stage_name="beta",
                logging_level=apigw.MethodLoggingLevel.INFO,
                data_trace_enabled=False,
                metrics_enabled=True,
                throttling_rate_limit=50,
                throttling_burst_limit=20,
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

        backend_integration = apigw.LambdaIntegration(
            backend_fn,
            proxy=True,
            allow_test_invoke=False,
        )

        api.root.add_method("ANY", backend_integration)
        proxy = api.root.add_resource("{proxy+}")
        proxy.add_method("ANY", backend_integration)

        # ── S3 Geo Assets Bucket ──────────────────────────────────────────────
        # Stores static geo data files served by the backend or referenced by frontend.
        # IP-restricted, publicly readable from allowed IPs only.
        assets_bucket = s3.Bucket(
            self, "MindmapGeoAssetsBucket",
            bucket_name=f"pai-mindmap-geo-assets-{self.account}",
            public_read_access=True,
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=False,
                block_public_policy=False,
                ignore_public_acls=False,
                restrict_public_buckets=False,
            ),
            removal_policy=cdk.RemovalPolicy.RETAIN,
        )

        assets_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.DENY,
                principals=[iam.AnyPrincipal()],
                actions=["s3:GetObject"],
                resources=[assets_bucket.arn_for_objects("*")],
                conditions={
                    "NotIpAddress": {
                        "aws:SourceIp": allowed_ips,
                    }
                },
            )
        )

        # ── S3 Frontend Bucket ────────────────────────────────────────────────
        # Hosts the compiled React (Vite) frontend.
        # After CDK deploy, build frontend and upload:
        #   cd frontend
        #   VITE_API_URL=<ApiGatewayUrl> npm run build
        #   aws s3 sync dist s3://<FrontendBucketName> --delete
        frontend_bucket = s3.Bucket(
            self, "MindmapGeoFrontendBucket",
            bucket_name=f"pai-mindmap-geo-frontend-{self.account}",
            website_index_document="index.html",
            website_error_document="index.html",
            public_read_access=True,
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=False,
                block_public_policy=False,
                ignore_public_acls=False,
                restrict_public_buckets=False,
            ),
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        frontend_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.DENY,
                principals=[iam.AnyPrincipal()],
                actions=["s3:GetObject"],
                resources=[frontend_bucket.arn_for_objects("*")],
                conditions={
                    "NotIpAddress": {
                        "aws:SourceIp": allowed_ips,
                    }
                },
            )
        )

        # ── Outputs ───────────────────────────────────────────────────────────
        cdk.CfnOutput(
            self, "ApiGatewayUrl",
            value=api.url,
            description="API Gateway URL — set as VITE_API_URL when building frontend",
        )
        cdk.CfnOutput(
            self, "FrontendBucketName",
            value=frontend_bucket.bucket_name,
            description="S3 bucket — upload React build output here",
        )
        cdk.CfnOutput(
            self, "FrontendUrl",
            value=frontend_bucket.bucket_website_url,
            description="mindmap-geo frontend URL (S3 website endpoint)",
        )
        cdk.CfnOutput(
            self, "AssetsBucketName",
            value=assets_bucket.bucket_name,
            description="S3 bucket for geo static assets",
        )
        cdk.CfnOutput(
            self, "AllowedIps",
            value=", ".join(allowed_ips),
            description="IP addresses allowed to access the API and frontend",
        )
