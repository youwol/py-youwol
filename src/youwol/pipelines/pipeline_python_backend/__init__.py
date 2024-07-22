"""
The purpose of this :func:`pipeline <youwol.pipelines.pipeline_python_backend.pipeline.pipeline>`
is to package and publish a custom python backend.
They are running separately from the youwol server on specific port,
and proxied from the youwol server using a
:class:`RedirectSwitch <youwol.app.environment.models.flow_switches.RedirectSwitch>`.

A simple project's template generator is provided through this
:func:`function <youwol.pipelines.pipeline_python_backend.template.template>`.

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

    For a :class:`FuturesResponse <youwol.utils.utils_requests.FuturesResponse>`:
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
