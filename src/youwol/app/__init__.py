"""
This module defines the YouWol server application
(:glob:``fastapi_app` <youwol.app.fastapi_app.fastapi_app>`).
 None of the services defined in this module are accessible online;
 refer to the :mod:`backends <youwol.backends>` module for services available online.

It encompasses the following submodules:

- :mod:`environment <youwol.app.environment>`: Components regarding runtime information of the
current environment.
- :mod:`middlewares <youwol.app.middlewares>`: The middlewares used in the local server.
- :mod:`middlewares <youwol.app.routers>`: The HTTP routers, specifying the available endpoints for
 the local server.

Communication with the local server can be achieved through two mechanisms:

- **HTTP calls**: Utilized for most endpoints defined in the :mod:`routers <youwol.app.routers>`.
Each HTTP call results in a single HTTP response.
- **Web Sockets**: Employed for sending updates related to tasks handled by the server, such as asset downloads,
 step execution, and logs. Web Sockets are also useful for transmitting updates and results from lengthy computations.

The Typescript project [`@youwol/local-youwol-client`](https://github.com/youwol/local-youwol-client) offers
javascript utilities to consume both of these communication methods.
"""
