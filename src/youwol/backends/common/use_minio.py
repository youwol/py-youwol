# standard library
import os

# third parties
from minio import Minio

# Youwol utilities
from youwol.utils.servers.env import MINIO, Env, minio_endpoint

required_env_vars = MINIO
not_founds = [v for v in required_env_vars if not os.getenv(v.value)]
if not_founds:
    raise RuntimeError(f"Missing environments variable: {not_founds}")
minio_host = os.getenv(Env.MINIO_HOST.value)
minio_access_key = os.getenv(Env.MINIO_ACCESS_KEY.value)
minio_secret_key = os.getenv(Env.MINIO_ACCESS_SECRET.value)
minio = Minio(
    endpoint=minio_endpoint(minio_host=minio_host),
    access_key=minio_access_key,
    secret_key=minio_secret_key,
    secure=False,
)
