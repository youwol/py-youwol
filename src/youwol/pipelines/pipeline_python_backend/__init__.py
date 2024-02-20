"""
The purpose of this [pipeline](@yw-nav-func:youwol.pipelines.pipeline_python_backend.pipeline.pipeline)
is to package and publish a custom python backend.
They are running separately from the youwol server on specific port,
and proxied from the youwol server using a
[RedirectSwitch](@yw-nav-class:RedirectSwitch).

A simple project's template generator is provided through this
[function](@yw-nav-func:youwol.pipelines.pipeline_python_backend.template.template).

Stack:
    * **programing language**: [python](https://www.python.org/)
    * **frameworks**: [FastAPI](https://fastapi.tiangolo.com/)

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
