"""
This module gathers the definition of pipeline provided by youwol, developers can create and share their own pipelines
(through PiPy modules for instance).

Pipelines define abstraction to work with project (python backends, javascript applications, typescript projects,
 *etc.*) using a particular stack. They basically formalize how to initialize, build, test, and deploy,
 among others steps.

"""

# relative
from .publish_cdn import *
