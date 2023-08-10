# standard library
import os

# Youwol utilities
from youwol.utils.servers.env import OPENID_BASE_URL, Env

required_env_vars = OPENID_BASE_URL

not_founds = [v for v in required_env_vars if not os.getenv(v.value)]
if not_founds:
    raise RuntimeError(f"Missing environments variable: {not_founds}")

openid_base_url = os.getenv(Env.OPENID_BASE_URL.value)
