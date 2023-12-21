# standard library
import os

# Youwol utilities
from youwol.utils.servers.env import OPENID_BASE_URL, Env

# relative
from .env import get_not_empty_env_value

required_env_vars = OPENID_BASE_URL

not_founds = [v for v in required_env_vars if not os.getenv(v.value)]
if not_founds:
    raise RuntimeError(f"Missing environments variable: {not_founds}")

openid_base_url = get_not_empty_env_value(Env.OPENID_BASE_URL)
