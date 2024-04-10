import { AnyVirtualDOM } from '@youwol/rx-vdom'

const typingUrl = 'https://docs.python.org/3/library/typing.html'

export interface Configuration {
    decoratorView: ({ path }: { path: string }) => AnyVirtualDOM | undefined
    externalTypes: { [k: string]: string }
    codeUrl: (path: string, startLine: number) => string
}

export const configuration = {
    decoratorView: ({ path }: { path: string }) => {
        const httpMethods = ['get', 'post', 'put', 'delete']
        for (const method of httpMethods) {
            if (path.includes(`router.${method}`)) {
                const match = path.match(/'(.*?)'/)
                return (
                    match && {
                        tag: 'div' as const,
                        class: 'd-flex align-items-center',
                        children: [
                            {
                                tag: 'div' as const,
                                class: 'font-weight-bolder mr-2',
                                innerText: `${method.toUpperCase()}:`,
                            },
                            {
                                tag: 'div' as const,
                                innerText: match[1],
                            },
                        ],
                    }
                )
            }
        }
    },
    codeUrl: (path: string, startLine: number) => {
        return `https://github.com/youwol/py-youwol/tree/main/src/${path}#L${startLine}`
    },
    externalTypes: {
        Exception: 'https://docs.python.org/3/tutorial/errors.html',
        bytes: 'https://docs.python.org/3/library/stdtypes.html#bytes-and-bytearray-operations',
        str: 'https://docs.python.org/fr/3/library/string.html',
        bool: 'https://docs.python.org/fr/3/library/stdtypes.html#boolean-type-bool',
        int: 'https://docs.python.org/fr/3/library/stdtypes.html#numeric-types-int-float-complex',
        float: 'https://docs.python.org/fr/3/library/stdtypes.html#numeric-types-int-float-complex',
        list: 'https://docs.python.org/3/library/stdtypes.html#lists',
        dict: 'https://docs.python.org/3/library/stdtypes.html#mapping-types-dict',
        set: 'https://docs.python.org/3/library/stdtypes.html#set',
        tuple: 'https://docs.python.org/3/library/stdtypes.html#tuple',
        'asyncio.subprocess.Process':
            'https://docs.python.org/3/library/asyncio-subprocess.html',
        'collections.abc.Mapping':
            'https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping',
        'io.BytesIO': 'https://docs.python.org/3/library/io.html#io.BytesIO',
        'enum.Enum': 'https://docs.python.org/3/library/enum.html',
        'abc.ABC': 'https://docs.python.org/3/library/abc.html',
        'collections.abc.Awaitable':
            'https://docs.python.org/3/library/collections.abc.html#collections.abc.Awaitable',
        'pathlib.Path':
            'https://docs.python.org/fr/3/library/pathlib.html#pathlib.Path',
        'typing.List': `${typingUrl}#typing.List`,
        'typing.Dict': `${typingUrl}#typing.Dict`,
        'typing.Tuple': `${typingUrl}#typing.Tuple`,
        'typing.Optional': `${typingUrl}#typing.Optional`,
        'typing.Union': `${typingUrl}#typing.Union`,
        'typing.Any': `${typingUrl}#typing.Any`,
        'typing.Mapping': `${typingUrl}#typing.Mapping`,
        'typing.Awaitable': `${typingUrl}#typing.Awaitable`,
        'typing.Callable': `${typingUrl}#typing.Callable`,
        'typing.Set': `${typingUrl}#typing.Set`,
        'typing.NamedTuple': `${typingUrl}#typing.NamedTuple`,
        'typing.Literal': `${typingUrl}#typing.Literal`,
        'typing.Generic': 'https://mypy.readthedocs.io/en/stable/generics.html',
        'asyncio.Future':
            'https://docs.python.org/3/library/asyncio-future.html',
        'aiohttp.ClientSession':
            'https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession',
        'aiohttp.ClientResponse':
            'https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientResponse',
        'pydantic.BaseModel': `https://docs.pydantic.dev/latest/api/base_model/`,
        'starlette.requests.Request': 'https://www.starlette.io/requests/',
        'starlette.responses.JSONResponse':
            'https://www.starlette.io/responses/#jsonresponse',
        'starlette.responses.FileResponse':
            'https://www.starlette.io/responses/#fileresponse',
        'starlette.responses.Response':
            'https://www.starlette.io/responses/#response',
        'starlette.websockets.WebSocket':
            'https://www.starlette.io/websockets/',
        'fastapi.Request':
            'https://fastapi.tiangolo.com/reference/request/?h=class+request',
        'fastapi.HTTPException':
            'https://fastapi.tiangolo.com/reference/exceptions/',
        'fastapi.APIRouter':
            'https://fastapi.tiangolo.com/reference/apirouter/?h=apir',
        'fastapi.FastAPI':
            'https://fastapi.tiangolo.com/reference/fastapi/?h=fastapi',
        'fastapi.UploadFile':
            'https://fastapi.tiangolo.com/reference/uploadfile/',
        'jwt.PyJWKClient':
            'https://github.com/jpadilla/pyjwt/tree/master?tab=readme-ov-file',
        'minio.Minio':
            'https://min.io/docs/minio/linux/developers/python/API.html',
        'watchdog.events.PatternMatchingEventHandler':
            'https://pythonhosted.org/watchdog/api.html#watchdog.events.PatternMatchingEventHandler',
        'watchdog.events.FileSystemEvent':
            'https://pythonhosted.org/watchdog/api.html#watchdog.events.FileSystemEvent',
        'threading.Thread':
            'https://docs.python.org/3/library/threading.html#threading.Thread',
    },
}
