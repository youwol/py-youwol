from aiohttp import ClientSession, TCPConnector
from starlette.requests import Request
from starlette.responses import Response

from starlette.datastructures import Headers

from youwol.context import Context


async def get_headers(context: Context) -> Headers:
    with_headers = await context.config.userConfig.general.localGateway.with_headers(context)
    return Headers(headers={**context.request.headers, **with_headers})


async def redirect_api_remote(request: Request, context: Context):
    # One of the header item leads to a server error ... for now only provide authorization
    # headers = {k: v for k, v in request.headers.items()}
    headers = {"Authorization": request.headers.get("authorization")}

    return await redirect_request(
        incoming_request=request,
        origin_base_path="/api",
        destination_base_path="https://gc.platform.youwol.com/api",
        headers=headers,
        context=context
        )


async def redirect_request(
        incoming_request: Request,
        origin_base_path: str,
        destination_base_path: str,
        context,
        headers=None
        ):
    rest_of_path = incoming_request.url.path.split(origin_base_path)[1].strip('/')
    headers = {k: v for k, v in incoming_request.headers.items()} if not headers else headers
    redirect_url = f"{destination_base_path}/{rest_of_path}"

    async def forward_response(response):
        headers_resp = {k: v for k, v in response.headers.items()}
        content = await response.read()
        return Response(status_code=response.status, content=content, headers=headers_resp)

    params = incoming_request.query_params
    # after this eventual call, a subsequent call to 'body()' will hang forever
    data = await incoming_request.body() if incoming_request.method in ['POST', 'PUT', 'DELETE'] else None

    async with ClientSession(connector=TCPConnector(verify_ssl=False), auto_decompress=False) as session:

        if incoming_request.method == 'GET':
            async with await session.get(url=redirect_url, params=params, headers=headers) as resp:
                return await forward_response(resp)

        if incoming_request.method == 'POST':
            async with await session.post(url=redirect_url, data=data, params=params, headers=headers) as resp:
                return await forward_response(resp)

        if incoming_request.method == 'PUT':
            async with await session.put(url=redirect_url, data=data, params=params, headers=headers) as resp:
                return await forward_response(resp)

        if incoming_request.method == 'DELETE':
            async with await session.delete(url=redirect_url, data=data,  params=params, headers=headers) as resp:
                return await forward_response(resp)
