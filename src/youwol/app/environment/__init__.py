"""
This module gather the information regarding running environment at a particular point in time.

It essentially converts the :class:`Configuration <youwol.app.environment.models.models_config.Configuration>`
provided by the user into an instance of
:class:`YouwolEnvironment <youwol.app.environment.youwol_environment.YouwolEnvironment>`, defining the current
run-time.

Note:
    The current environment is available each time an instance of :class:`Context <utils.context.context.Context>`
    is, using:
    <code-snippet language="python">
    ctx: Context # some instance of Context
    yw_env = await ctx.get('env', YouwolEnvironment)
    </code-snippet>
"""

# relative
from .clients import *
from .config_from_module import *
from .local_auth import *
from .models import *
from .online_environments import *
from .paths import *
from .python_dynamic_loader import *
from .youwol_environment import *
