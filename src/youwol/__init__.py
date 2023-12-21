"""
This is the route module of the PiPy package [youwol](https://pypi.org/project/youwol/).
Its code is oopen source and available on [GitHUB](https://github.com/youwol/py-youwol).

It gathers the following submodules:
*  **`app`**: the components required by the local server only. It is about routers, middlewares and environment
essentially.
*  **`backend`**: the components (backends) that are both instantiated by the local server, and deployed
in the cloud environment (`https://platform.youwol.com` is the official cloud environment)
*  **`utils`** submodule: standalone module providing utilities useful in
multiple context. It provides solutions for logging, http clients and various other helpers.
*  **`pipelines`**: it provides multiple definition of pipelines used in youwol. Pipelines define abstraction
to work with project (python backends, javascript applications, typescript projects, *etc.*)  using a particular stack.
They basically formalize how to initialize, build, test, and deploy among others steps.
This module encapsulates a couple of pipelines, developers can create and share their own pipelines (through PiPy
modules for instance).

"""
