from starlette.requests import Request

from routers.api import redirect_get_api, redirect_post_api, redirect_put_api, redirect_delete_api, redirect_get


async def redirect_api_remote(request: Request, redirect_url: str = None):

    new_path = redirect_url if redirect_url else f'https://gc.platform.youwol.com{request.url.path}'
    # One of the header item leads to a server error ... for now only provide authorization
    # headers = {k: v for k, v in request.headers.items()}
    headers = {"Authorization": request.headers.get("authorization")}

    if request.method == 'GET':
        resp = await redirect_get(request, new_path, headers)
        return resp

    return None


async def redirect_api_local(request: Request, base_path: str, config: any):
    service_name = base_path.split('/api/')[1]
    rest_of_path = request.url.path.split(f'/{service_name}/')[1]
    if request.method == 'GET':
        return await redirect_get_api(request, service_name, rest_of_path, config)
    if request.method == 'POST':
        return await redirect_post_api(request, service_name, rest_of_path, config)
    if request.method == 'PUT':
        return await redirect_put_api(request, service_name, rest_of_path, config)
    if request.method == 'DELETE':
        return await redirect_delete_api(request, service_name, rest_of_path, config)
    pass
