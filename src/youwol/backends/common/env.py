# standard library
import os

# Youwol utilities
from youwol.utils.servers.env import Env


def get_not_empty_env_value(env: Env) -> str:
    v = os.getenv(env.value)
    if v is None:
        raise RuntimeError(f"Empty environemnt variable {env.value}")
    return v
