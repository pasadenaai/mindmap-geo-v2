"""Shared client config for talking to LocalStack from the seed/sync scripts.

LocalStack does not authenticate requests, so local clients are sent unsigned
rather than carrying credential literals in source. Real AWS clients keep using
the normal boto3 credential chain.
"""
from botocore import UNSIGNED
from botocore.config import Config

LOCAL_CONFIG = Config(signature_version=UNSIGNED)

try:  # aioboto3 / aiobotocore clients want AioConfig
    from aiobotocore.config import AioConfig

    LOCAL_AIO_CONFIG = AioConfig(signature_version=UNSIGNED)
except ImportError:  # sync-only environments
    LOCAL_AIO_CONFIG = None
