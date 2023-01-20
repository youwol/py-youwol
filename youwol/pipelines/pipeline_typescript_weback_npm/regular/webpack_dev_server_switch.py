from typing import Optional

from starlette.requests import Request
from starlette.responses import Response

from youwol.environment import CdnSwitch
from youwol_utils import Context, encode_id, ResourcesNotFoundException


class WebpackDevServerSwitch(CdnSwitch):
    """
CDN resource are stored in the CDN database: each time a related resource is queried, it is retrieved from here.
The class WebpackDevServerSwitch can alter this behavior for a particular package,
 and serve the resources using a running webpack's dev-server.

**Attributes**:

- **packageName** :class:`str`
Name of the targeted package.

- **port** :class:`int`
Listening port of the dev-server.
"""

    packageName: str
    port: int

    async def switch(self,
                     incoming_request: Request,
                     context: Context) -> Optional[Response]:
        # for webpack dev server, there is two kinds of resources:
        #   - the one built by webpack (dynamic): they are served from the 'root'
        #     For instance: '/dist/bundles.js will be served at localhost:xxxx/bundle.js
        #     In this case we only care about the last part of the url
        #   - the static assets, they are served 'normally'
        #     For instance: '/dist/assets/foo.png' will be served at localhost:xxxx/dist/assets/foo.png
        #     In this case we care about last part of the url after the asset_id
        # The static case is tested first as usually there are a limited set of dynamic resources

        headers = context.headers(from_req_fwd=lambda header_keys: header_keys)

        asset_id = f"/{encode_id(self.packageName)}/"
        trailing_path = incoming_request.url.path.split(asset_id)[1]
        # the next '[1:]' skip the version of the package
        rest_of_path_static = '/'.join(trailing_path.split('/')[1:])
        rest_of_path_dynamic = trailing_path.split('/')[-1]

        resp = await self._forward_request(rest_of_path=rest_of_path_static, headers=headers)
        if resp:
            return resp

        resp = await self._forward_request(rest_of_path=rest_of_path_dynamic, headers=headers)
        if resp:
            return resp

        await context.error(text=f"WebpackDevServerSwitch[{self}]: Error status while dispatching",
                            data={
                                "origin": incoming_request.url.path,
                                "paths tested": [rest_of_path_static, rest_of_path_dynamic]
                            })
        raise ResourcesNotFoundException(
            path=f"{rest_of_path_dynamic} or ${rest_of_path_dynamic}",
            detail=f"No resource found"
        )
