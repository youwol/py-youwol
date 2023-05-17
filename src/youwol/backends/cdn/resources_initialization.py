# Youwol backends
from youwol.backends.cdn.configurations import Configuration


async def init_resources(_config: Configuration):
    print("### Ensure database resources => DISABLED ###")
