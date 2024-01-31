"""
The purpose of this pipeline is to package and publish a custom python backend.
They are running separately from the youwol server on specific port,
and proxied from the youwol server using a
[RedirectSwitch](@yw-nav-class:youwol.app.environment.models.models_config.RedirectSwitch).

Stack:
    * **programing language**: [python](https://www.python.org/)
    * **frameworks**: [FastAPI](https://fastapi.tiangolo.com/)

Template:
    A project's template generator is provided [here](), it can be referenced in your configuration file using
     [ProjectTemplate](@yw-nav-class:youwol.app.environment.models.models_config.ProjectTemplate) object:
    ```python
    from youwol.app.environment import (
        Configuration,
        Projects,
        RecursiveProjectsFinder
    )
    from youwol.pipelines.pipeline_python_backend import template

    projects_folder = Path.home() / 'Projects'

    Configuration(
        projects=Projects(
            finder=RecursiveProjectsFinder(
                fromPaths=[projects_folder],
            ),
            templates=[template(folder=projects_folder / 'auto-generated')],
        )
    )
    ```

Warning:
    Do not forget to provide the definition of the
    [RedirectSwitch](@yw-nav-class:youwol.app.environment.models.models_config.RedirectSwitch)
    associated to the backend in your configuration file.
     E.g. for a backend served on the port `4002` and expected to be proxied on
    `/api/foo-backend`:
    ```python
    from youwol.app.environment import (
        Configuration,
        Customization,
        CustomMiddleware,
        RedirectSwitch,
        FlowSwitcherMiddleware
    )
    redirect_switch = RedirectSwitch(
        origin="/api/foo-backend",
        destination=f"http://localhost:4002"
    )

    Configuration(
        customization=Customization(
            middlewares=[
                FlowSwitcherMiddleware(
                    name="Backends",
                    oneOf=[redirect_switch],
                )
            ],
        )
    )
    ```

Todos:
    Provides an auto-generated client on e.g. `/client`.
    This will allow to easily consume the backend from javascript

    For a simple response:
    ```js
    const {testBackend} = await youwol.install({
        backends: ['test-backend' as testBackend]
    })
    client = await testBackend.client()
    resp = await client.readFile({fileId})
    console.log(resp)
    ```

    For a [FuturesResponse](@yw-nav-class:youwol.utils.utils_requests.FuturesResponse):
    ```js
    const {testBackend} = await youwol.install({
        backends: ['test-backend' as testBackend]
    })
    client = await testBackend.client()
    resp = await client.asyncJob({taskId})
    console.log(resp)
    resp.channel$.subscribe((result) => {
        console.log("got result", result)
    })
    ```

"""
# relative
from .pipeline import *
from .template import *
