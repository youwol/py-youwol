# Couple of examples of py-youwol configuration

This repo gather typical examples of py-youwol configuration,
they are located at the root of the repo.

* [empty_config.py](empty_config.py): illustrates empty (initial) configuration.
* [system_config_browser_auth.py](system_config_browser_auth.py): illustrates how to plug multiple cloud environments.
  Authentication by browser.
* [system_config_direct_auth.py](system_config_direct_auth.py): illustrates how to connect on
  a provided environment using direct flow authentication.
* [projects_config.py](projects_config.py): illustrates how to use pipelines to manage projects.
* [customization_endpoints.py](customization_endpoints.py): illustrates how to add custom endpoints to the environment[^pythonpath].
* [customization_middlewares.py](customization_middlewares.py): illustrates how to add custom middlewares
  to the environment.
* [customization_events.py](customization_events.py): illustrates how to react to environment's events.

[^pythonpath]: Need the variable `PYTHONPATH` to include this directory, such as:  
  `$ PYTHONPATH=doc/examples/configs youwol --conf doc/examples/configs/customization_endpoints.py`
