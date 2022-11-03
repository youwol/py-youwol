from starlette.responses import Response

from youwol_assets_gateway.routers.common import assert_read_permissions_from_raw_id


from fastapi import APIRouter, Depends
from starlette.requests import Request

from youwol_utils import HTTPException
from youwol_utils.context import Context
from youwol_assets_gateway.configurations import Configuration, get_configuration

router = APIRouter(tags=["assets-gateway.deprecated"])


@router.get("/raw/{kind}/{raw_id}/{rest_of_path:path}",
            summary="get raw record DEPRECATED")
async def get_raw(
        request: Request,
        kind: str,
        rest_of_path: str,
        raw_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    """
    This end point is deprecated, it is used in following circumstances (only related to cdn):
        - in @youwol/cdn-client/client.ts: the url constructed to fetch cdn files use:
         `/api/assets-gateway/raw/package/${cdn_url}`
         => it needs to be updated by `/api/assets-gateway/cdn-backend/resources/${cdn_url}`
         - in saved flux project and stories the above URL are 'pined' in a sort of '.lock' files
         => these project need to be updated after the first point is solved
    """
    async with Context.start_ep(
            request=request,
            with_attributes={"raw_id": raw_id, "path": rest_of_path}
    ) as ctx:
        if kind != "package":
            raise HTTPException(status_code=410, detail="Only 'package' kind is kept under get-raw.")
        version = rest_of_path.split('/')[0]
        rest_of_path = '/'.join(rest_of_path.split('/')[1:])
        await assert_read_permissions_from_raw_id(raw_id=raw_id, configuration=configuration, context=ctx)

        async def reader(resp_cdn):
            resp_bytes = await resp_cdn.read()
            return Response(content=resp_bytes, headers={k: v for k, v in resp_cdn.headers.items()})

        resp = await configuration.cdn_client.get_resource(
            library_id=raw_id,
            version=version,
            rest_of_path=rest_of_path,
            reader=reader,
            auto_decompress=False,
            headers=ctx.headers())

        return resp
