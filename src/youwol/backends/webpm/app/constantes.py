PROXIED_HEADERS_CONTENT = [
    "content-length",
    "content-encoding",
]
PROXIED_HEADERS_CACHE = [
    "cache-control",
    "pragma",
    "expires",
    "etag",
    "last-modified",
    "age",
    "vary",
]
PROXIED_HEADERS_DEBUG = ["x-trace-id"]

PROXIED_HEADERS = [
    *PROXIED_HEADERS_CONTENT,
    *PROXIED_HEADERS_CACHE,
    *PROXIED_HEADERS_DEBUG,
]

CDN_CLIENT_ASSET_ID = "QHlvdXdvbC9jZG4tY2xpZW50"
CDN_CLIENT_ASSET_PATH = "dist/@youwol/cdn-client.js"
CDN_CLIENT_ASSET_PATH_SOURCE_MAP = f"{CDN_CLIENT_ASSET_PATH}.map"

WEBPM_CLIENT_ASSET_ID = "QHlvdXdvbC93ZWJwbS1jbGllbnQ="
WEBPM_CLIENT_ASSET_PATH = "dist/@youwol/webpm-client.js"
WEBPM_CLIENT_ASSET_PATH_SOURCE_MAP = f"{WEBPM_CLIENT_ASSET_PATH}.map"
