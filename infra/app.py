#!/usr/bin/env python3
"""
mindmap-geo Lambda CDK App
Beta deployment: Lambda + API Gateway + S3, no NAT/ALB/Fargate.
~$2/month. IP-restricted to allowed_ips context variable.

Usage:
  # Find your IP first:
  curl https://checkip.amazonaws.com

  # Bootstrap (one-time per account/region):
  cdk bootstrap aws://<ACCOUNT_ID>/us-east-1 --profile <PROFILE>

  # Deploy:
  cdk deploy MindmapGeoLambdaStack \
    --context allowed_ips=YOUR.IP.HERE/32 \
    --profile <PROFILE>
"""

import os

import aws_cdk as cdk
from mindmap_geo_lambda_stack import MindmapGeoLambdaStack

app = cdk.App()

MindmapGeoLambdaStack(
    app,
    "MindmapGeoLambdaStack",
    env=cdk.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],  # resolved by the CDK CLI from the active profile
        region="us-east-1",
    ),
    description="mindmap-geo beta: Lambda + API Gateway + S3 (~$2/month, IP-restricted)",
)

app.synth()
