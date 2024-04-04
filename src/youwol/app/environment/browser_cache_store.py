# standard library
import base64
import binascii
import dataclasses
import datetime
import json
import re
import time

from inspect import isawaitable
from pathlib import Path

# typing
from typing import NamedTuple, TextIO

# third parties
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import Response

# Youwol application
from youwol.app.environment.models.models_config import Configuration

# Youwol utilities
from youwol.utils import Context, YouwolHeaders, log_info
from youwol.utils.crypto.digest import compute_digest


class BrowserCacheItem(BaseModel):
    """
    Represents an item in the [BrowserCacheStore](@yw-nav-class:BrowserCacheStore).
    """

    key: str
    """
    Item's key
    """
    file: str
    """
    Associated file on disk.
    """
    headers: dict[str, str]
    """
    Associated headers of the response.
    """
    expirationTime: float
    """
    Expiration time (EPOCH).
    """


class BrowserCacheResponse(NamedTuple):
    """
    The response when recovered from the YouWol browser cache using
    [BrowserCacheStore.try_get](@yw-nav-meth:BrowserCacheStore.try_get).
    """

    response: Response
    """
    The HTTP response.
    """
    item: BrowserCacheItem
    """
    The entry in the cache.
    """


@dataclasses.dataclass
class BrowserCacheStore:
    """
    Class responsible for managing the emulated browser cache within YouWol.
    Configuration settings are inherited from the [BrowserCache](@yw-nav-class:models_config.BrowserCache) class,
    its documentation provides the rationales and overall explanations of this layer.

    Caching a resource within this store is an opt-in feature chosen by the backend that initially serves the resource.
    This functionality operates by modifying a `Response` accordingly, utilizing a specific header. Here's an example:

    <code-snippet language="python">
    info = YwBrowserCacheDirective(
        # Name of the backend serving the resource
        service="cdn-backend",
        # Path to the file on the disk
        filepath=f"{configuration.file_system.root_path}/{path}",
    )
    # Assuming a 'resp' Response is already available.
    YouwolHeaders.set_yw_browser_cache_directive(info=info, response=resp)
    </code-snippet>

    """

    yw_config: Configuration

    def __post_init__(self):
        self._file_key: str | None = None
        self._output_file: TextIO | None = None
        self._output_file_path: Path | None = None
        self._items: dict[str, BrowserCacheItem] = {}

    async def cache_if_needed(
        self, request: Request, response: Response, context: Context
    ) -> BrowserCacheItem | None:
        """
        Persists a response into the cache if required.

        Conditions for caching:
        *  The cache is properly initialized.
        *  The incoming request is a `GET` request and originates directly from the browser.
        *  The response is explicitly marked for caching via the
           [YouwolHeaders.yw_browser_cache_directive](@yw-nav-attr:YouwolHeaders.yw_browser_cache_directive) header.
        *  The `cache-control` header in the response does not include any of `["no-cache", "no-store", "max-age=0"]`,
           but explicitly includes a `max-age` directive.
        *  the [BrowserCache.ignore](@yw-nav-attr:models_config.BrowserCache.ignore) attribute does not resolve to
        `True`.
        *  the [BrowserCache.disable_write](@yw-nav-attr:models_config.BrowserCache.disable_write) attribute does not
        resolve to `True`.

        Parameters:
            request: The incoming request.
            response: The outgoing response.

        Return:
            The cached item if the response has been cached, otherwise None.
        """

        if not self._init_cache(request=request):
            return

        if not self._is_get_request_from_browser(request=request):
            return

        if YouwolHeaders.yw_browser_cache_directive not in response.headers:
            return

        if any(
            d in response.headers.get("cache-control")
            for d in ["no-cache", "no-store", "max-age=0"]
        ):
            return

        if "max-age=" not in response.headers.get("cache-control"):
            return

        if await self._ignore(request, context):
            return

        if await self._disable_write(request, response, context):
            return

        key = self._get_key(request=request)
        info = YouwolHeaders.get_youwol_browser_cache_info(response=response)
        item = BrowserCacheItem(
            key=key,
            file=info.filepath,
            headers=dict(response.headers.items()),
            expirationTime=self._get_expiration_time(
                response.headers.get("cache-control")
            ),
        )
        self._items[key] = item
        if self._output_file:
            self._write_items(items=[item], fp=self._output_file)

        return item

    async def try_get(
        self, request: Request, context: Context
    ) -> BrowserCacheResponse | None:
        """
        Tries to retrieve a cached response from an incoming request.

        Conditions to succeed:
        *  The cache is properly initialized.
        *  The incoming request is a `GET` request and originates directly from the browser.
        *  the [BrowserCache.ignore](@yw-nav-attr:models_config.BrowserCache.ignore) attribute does not resolve to
        `True`.
        *  The key computed from the incoming request is associated to an item in the cache.
        *  The file associated to the item does exist on the disk.
        *  The content-length of the file did not change since the original publication.

        Parameters:
            request: The incoming request.
            context: Current executing context.

        Return:
            The cached response & item if the function succeed, otherwise None.
        """
        if not self._init_cache(request=request):
            return

        if not self._is_get_request_from_browser(request=request):
            return

        if await self._ignore(request, context):
            return

        key = self._get_key(request=request)

        if key not in self._items:
            return

        item = self._items[key]
        file_path = Path(item.file)
        if not file_path.exists():
            self._items.pop(key)
            return

        range_header = request.headers.get("Range")
        if range_header:
            # If Range header is present, serve the requested range of bytes
            start, end = range_header.split("=")[-1].split("-")
            start = int(start)
            end = int(end) if end else None

            with open(file_path, "rb") as file:
                file.seek(start)
                content = file.read(end - start + 1) if end else file.read()

            response = Response(
                content=content,
                status_code=206,
                headers={
                    **item.headers,
                    "Content-Range": f"bytes {start}-{end}/{file_path.stat().st_size}",
                    YouwolHeaders.youwol_origin: "browser-cache",
                },
            )
            return BrowserCacheResponse(response=response, item=item)

        content = file_path.read_bytes()
        if (
            "content-length" in item.headers
            and str(len(content)) != item.headers["content-length"]
        ):
            await context.warning(
                text=f"The resource at {file_path} was initially chosen for caching, but its content has since changed",
                data=item,
            )
            return

        response = Response(
            status_code=200,
            content=content,
            headers={**item.headers, YouwolHeaders.youwol_origin: "browser-cache"},
        )
        return BrowserCacheResponse(response=response, item=item)

    def stop(self):
        """
        Closes the underlying file on disk if [BrowserCache.mode](@yw-nav-attr:models_config.BrowserCache.mode)
        is `disk`.
        """
        if self._output_file:
            log_info("BrowserCacheStore: close file")
            self._output_file.close()

    def items(self) -> list[BrowserCacheItem]:
        """
        Returns a copy of in-memory cached items.
        """
        return [BrowserCacheItem(**item.dict()) for item in self._items.values()]

    def output_file_path(self) -> Path:
        """
        Returns the path of the persisted file on disk
        (if [BrowserCache.mode](@yw-nav-attr:models_config.BrowserCache.mode) is `disk`).
        """
        return self._output_file_path

    def session_key(self) -> str:
        """
        Returns the session key of the cache.
        """
        return self._file_key

    async def clear(self, memory: bool, file: bool, context: Context) -> int:
        """
        Clears the cache entries, in-memory and/or in file (if applicable).

        Parameters:
            memory: If `True`, clear in-memory cached items.
            file: If `True`, clear associated file (if applicable: `mode` is `disk`).
            context: Current executing context.

        Return:
            Number of items deleted.
        """
        async with context.start(action="BrowserCacheStore.clear") as ctx:
            items_count = len(self._items)
            await ctx.info(
                text=f"Clear {items_count} cached items in memory",
                data={"memory": memory, "file": file},
            )
            if memory:
                await ctx.info(text="Clear in-memory items")
                self._items.clear()

            if file and self.yw_config.system.browserEnvironment.cache.mode == "disk":
                await ctx.info(text="Clear file")
                self._output_file.truncate(0)
                self._output_file.write(self._headline())

            return items_count

    def _init_cache(self, request: Request) -> bool:
        if self._file_key:
            # It means cache has been initialized
            return True

        if not hasattr(request.state, "user_info"):
            return False

        if self.yw_config.system.browserEnvironment.cache.mode == "in-memory":
            _ = self._get_session_key(request)
            # The initialization is OK, no output file is needed here.
            return True

        log_info(
            message="BrowserCacheStore: recover cached entries from persisted file..."
        )

        cache_dir = Path(self.yw_config.system.browserEnvironment.cache.cachesFolder)
        cache_dir.mkdir(parents=True, exist_ok=True)
        self._output_file_path = (
            cache_dir / self._get_session_key(request)
        ).with_suffix(".txt")
        if not self._output_file_path.exists():
            with open(self._output_file_path, "a", encoding="UTF-8") as fp:
                fp.write(self._headline())

        corrupted = []
        expired = []
        duplicates = False

        def sanity_check(item: BrowserCacheItem | None):
            if not item or not Path(item.file).exists():
                corrupted.append(item)
                return False

            if time.time() > item.expirationTime:
                expired.append(item)
                return False
            return True

        max_count = self.yw_config.system.browserEnvironment.cache.maxCount

        with open(self._output_file_path, encoding="UTF-8") as file:
            content = file.read()
            lines = content.split("\n")[1:]
            items = [
                BrowserCacheStore._decode_line(line) for line in lines if line != ""
            ]
            items = [item for item in items if sanity_check(item)]
            self._items = {**self._items, **{item.key: item for item in items}}
            log_info(
                message=f"BrowserCacheStore: loaded {len(items)} documents from {self._output_file_path}"
            )
            if len(self._items.keys()) != len(items):
                log_info(
                    message=f"BrowserCacheStore: found {len(items) - len(self._items.keys())} duplicated items, "
                    f"only the latest will be kept."
                )
                duplicates = True

            if len(self._items.keys()) > max_count:
                log_info(
                    message=f"BrowserCacheStore: maximum count of cached items reached "
                    f"({self._items.keys()}/{max_count})."
                )

            if corrupted:
                log_info(
                    message=f"BrowserCacheStore: found {len(corrupted)} corrupted items, proceed to remove them"
                )

        if duplicates or corrupted or expired or len(items) > max_count:
            with open(self._output_file_path, "w", encoding="UTF-8") as fp:
                fp.write(self._headline())
                items_to_keep = list(self._items.values())[-max_count:]
                self._write_items(items=items_to_keep, fp=fp)

        # The pointer is kept in memory to avoid extra opening each time writing is needed.
        # The 'stop()' method is required to be called each time a config. is reloaded or when py-youwol is terminated.
        # This is executed in `YouwolEnvironmentFactory`.
        self._output_file = open(  # pylint: disable=consider-using-with
            self._output_file_path, "a", encoding="UTF-8"
        )
        return True

    def _get_session_key(self, request: Request):
        if self._file_key:
            return self._file_key

        cache_config = self.yw_config.system.browserEnvironment.cache
        self._file_key = compute_digest(
            {
                "config_cache_key": cache_config.key(self.yw_config),
                "user_info": (
                    {
                        "name": request.state.user_info["sub"],
                        "groups": request.state.user_info["memberof"],
                    }
                ),
            },
            trace_path_root="YouwolEnvironment.getBrowserCacheKey",
        ).hex()
        return self._file_key

    def _get_key(self, request: Request):
        url = str(request.url).replace(
            f"http://localhost:{self.yw_config.system.httpPort}", ""
        )
        return f"{self._get_session_key(request=request)}@{url}"

    @staticmethod
    def _get_expiration_time(cache_control_header: str) -> float:
        max_age_pattern = re.compile(r"max-age=(\d+)")
        match = max_age_pattern.search(cache_control_header)

        if match:
            max_age = int(match.group(1))
            current_time = datetime.datetime.now(datetime.timezone.utc)
            expiration_time = current_time + datetime.timedelta(seconds=max_age)
            return expiration_time.timestamp()

        # This branch should not occur because 'max-age=' is explicitly asserted in `persist_if_needed`
        return datetime.datetime.now(datetime.timezone.utc).timestamp()

    def _write_items(self, items: list[BrowserCacheItem], fp: TextIO):
        for item in items:
            line = self._encode_line(item)
            fp.write(line + "\n")

    def _headline(self) -> str:
        return f"BrowserCacheStore V0 {self._file_key} \n"

    @staticmethod
    def _is_get_request_from_browser(request: Request) -> bool:
        if request.method != "GET":
            return False

        user_agent = request.headers.get("User-Agent", "")
        return any(
            keyword in user_agent.lower()
            for keyword in ["mozilla", "chrome", "safari", "firefox", "opera", "edge"]
        )

    @staticmethod
    def _encode_line(item: BrowserCacheItem) -> str:
        json_txt = json.dumps(item.dict())
        return base64.urlsafe_b64encode(str.encode(json_txt)).decode()

    @staticmethod
    def _decode_line(line: str) -> BrowserCacheItem | None:
        try:
            json_txt = base64.urlsafe_b64decode(str.encode(line)).decode()
        except binascii.Error:
            return None
        try:
            decoded = BrowserCacheItem(**json.loads(json_txt))
            return decoded
        except ValueError:
            return None

    async def _ignore(self, request: Request, context: Context) -> bool:
        ignore_config = self.yw_config.system.browserEnvironment.cache.ignore
        if ignore_config is None:
            return False

        args = (request, self.yw_config, context)
        return (
            await ignore_config(*args)
            if isawaitable(ignore_config)
            else ignore_config(*args)
        )

    async def _disable_write(
        self, request: Request, response: Response, context: Context
    ) -> bool:

        disable_config = self.yw_config.system.browserEnvironment.cache.disable_write
        if disable_config is None:
            return False

        args = (request, response, self.yw_config, context)
        return (
            await disable_config(*args)
            if isawaitable(disable_config)
            else disable_config(*args)
        )
