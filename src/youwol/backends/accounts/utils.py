# third parties
from starlette.requests import Request


def url_for(request: Request, function_name: str, https: bool, **params):
    url = request.url_for(function_name)
    if params:
        url.include_query_params(**params)
    url_str = str(url)
    if https:
        url_str = url_str.replace("http://", "https://")
    return url_str
