"""
This serves as the core module for the PiPy package [youwol](https://pypi.org/project/youwol/), with its open-source
 code available on [GitHub](https://github.com/youwol/py-youwol).

The module encompasses the following submodules:

*  :mod:`youwol.app`: Defines the YouWol local server application, covering environment details, middlewares,
and HTTP routers. It manages communication through both HTTP calls and Web Sockets.

*  :mod:`youwol.backends`: Encompasses the backends deployed in both local and online environments
(default: `https://youwol.platform.com`).

*  :mod:`youwol.utils`: A standalone module providing utilities applicable in various contexts.
It offers solutions for logging, HTTP clients, and various other helper functions.

*  :mod:`youwol.pipelines`: Pipelines introduce abstractions to work with projects (python backends,
javascript applications, typescript projects, etc.) using a specific stack.
They formalize steps such as initialization, building, testing, and deployment.
"""

__version__ = "0.1.12"
__release_version__ = "0.1.12"
