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

ASSET_ID = "QHlvdXdvbC9jZG4tY2xpZW50"
ASSET_PATH = "dist/@youwol/cdn-client.js"
ASSET_PATH_SOURCE_MAAP = f"{ASSET_PATH}.map"
