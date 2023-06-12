# standard library
import traceback

from abc import ABC, abstractmethod

# typing
from typing import Dict, List, Optional, Union

# third parties
from pydantic import BaseModel
from starlette.requests import Request

# Youwol utilities
from youwol.utils import decode_id
from youwol.utils.context import Label


def url_match(request: Request, pattern: str):
    method, regex = pattern.split(":")

    if method not in ("*", request.method):
        return False, None

    replaced = []
    if method == "*":
        replaced.append(request.method)
    parts_target = request.url.path.split("/")
    parts_regex = regex.split("/")
    if "**" not in parts_regex and len(parts_target) != len(parts_regex):
        return False, None
    if "**" in parts_regex and parts_regex.index("**") != len(parts_regex) - 1:
        raise ValueError("'**' can only be located at the trailing part of the pattern")

    for i, part in enumerate(parts_target):
        if i >= len(parts_regex):
            return False, None
        if i >= len(parts_regex) - 1 and parts_regex[-1] == "**":
            replaced.append([t for t in parts_target[i:] if t])
            return True, replaced
        if (
            i == len(parts_target) - 1
            and i + 1 < len(parts_regex)
            and parts_regex[i + 1] != "**"
        ):
            return False, None
        if part == parts_regex[i]:
            continue
        if parts_regex[i] == "*":
            replaced.append(part)
            continue

        return False, None

    return True, replaced


class RequestInfo(BaseModel):
    message: Optional[str]
    attributes: Dict[str, str] = {}
    labels: List[Label] = []


class RequestInfoExtractor(ABC):
    @abstractmethod
    def extract(self, request: Request) -> Optional[RequestInfo]:
        return NotImplemented


class PatternRequestInfoExtractor(RequestInfoExtractor):
    pattern: str

    def extract(self, request: Request) -> Optional[RequestInfo]:
        match, substitutes = url_match(request=request, pattern=self.pattern)
        if not match:
            return None
        return self.extract_from_pattern(substitutes)

    @abstractmethod
    def extract_from_pattern(
        self, substitutes: List[Union[str, List[str]]]
    ) -> RequestInfo:
        return NotImplemented


class All(PatternRequestInfoExtractor):
    pattern = "*:/**"

    def extract_from_pattern(self, substitutes: List[Union[str, List[str]]]):
        [method, messages] = substitutes
        if len(messages) != 0:
            *_, last = messages
        else:
            last = "root path"
        return RequestInfo(message=last, attributes={"method": method})


class Api(PatternRequestInfoExtractor):
    pattern = "*:/api/**"

    def extract_from_pattern(self, substitutes: List[Union[str, List[str]]]):
        [_method, [service, *_parts, last]] = substitutes
        return RequestInfo(message=last, attributes={"service": service})


class Admin(PatternRequestInfoExtractor):
    pattern = "*:/admin/**"

    def extract_from_pattern(self, substitutes):
        [*_, [service, *_]] = substitutes
        return RequestInfo(
            message=f"admin/{service}",
            attributes={"router": service},
            labels=[Label.ADMIN],
        )


class Logs(PatternRequestInfoExtractor):
    pattern = "*:/admin/system/logs/**"

    def extract_from_pattern(self, substitutes):
        return RequestInfo(
            message="logs", attributes={"service": "admin/logs"}, labels=[Label.LOG]
        )


class CdnAppsServer(PatternRequestInfoExtractor):
    pattern = "*:/applications/**"

    def extract_from_pattern(self, substitutes):
        try:
            [_, [a, b, *_]] = substitutes
        except ValueError:
            # e.g., for the 'healthz' end-point
            [_, a] = substitutes
            return RequestInfo(
                message=f"application ({a})",
                attributes={"service": "cdn-apps-server"},
                labels=[Label.APPLICATION],
            )

        resource = f"{a}/{b}" if a.startswith("@") else a
        return RequestInfo(
            message="application",
            attributes={"service": "cdn-apps-server", "resource": resource},
            labels=[Label.APPLICATION],
        )


class GetAssetGtwPackageMetadata(PatternRequestInfoExtractor):
    pattern = "GET:/api/assets-gateway/raw/package/metadata/**"

    def extract_from_pattern(self, substitutes):
        [[asset_id]] = substitutes
        return RequestInfo(
            message="asset metadata",
            attributes={"assetId": asset_id, "package": decode_id(asset_id)},
        )


class PutAssetGtwAccess(PatternRequestInfoExtractor):
    pattern = "PUT:/api/assets-gateway/assets/*/access/*"

    def extract_from_pattern(self, substitutes):
        [asset_id, grp_id] = substitutes
        return RequestInfo(
            message="Define access policy",
            attributes={"assetId": asset_id, "groupId": grp_id},
        )


class UpdateAssetGtwAsset(PatternRequestInfoExtractor):
    pattern = "POST:/api/assets-gateway/assets/*"

    def extract_from_pattern(self, substitutes):
        [asset_id] = substitutes
        return RequestInfo(message="Update asset", attributes={"assetId": asset_id})


class PutAssetGtwAsset(PatternRequestInfoExtractor):
    pattern = "PUT:/api/assets-gateway/assets/*/location/**"

    def extract_from_pattern(self, substitutes):
        [kind, _] = substitutes
        return RequestInfo(message="Create asset", attributes={"kind": kind})


class GetCDNPackageMetadata(PatternRequestInfoExtractor):
    pattern = "GET:/api/cdn-backend/libraries/*"

    def extract_from_pattern(self, substitutes):
        [raw_id] = substitutes
        return RequestInfo(message="Package metadata", attributes={"rawId": raw_id})


class GetCDNPackage1(PatternRequestInfoExtractor):
    pattern = "GET:/api/cdn-backend/libraries/*/*/*"

    def extract_from_pattern(self, substitutes):
        return RequestInfo(
            message="/".join(substitutes),
            attributes={
                "package": "/".join(substitutes[:-1]),
                "version": substitutes[-1],
            },
        )


class GetCDNPackage2(PatternRequestInfoExtractor):
    pattern = "GET:/api/cdn-backend/libraries/*/*"

    def extract_from_pattern(self, substitutes):
        if len(substitutes) >= 2:
            [name, version] = substitutes
            return RequestInfo(
                message=f"{name}/{version}",
                attributes={"package": name, "version": version},
            )
        name = substitutes[0]
        return RequestInfo(message=f"{name}", attributes={"package": name})


class GetTreedbItem(PatternRequestInfoExtractor):
    pattern = "GET:/api/treedb-backend/items/*"

    def extract_from_pattern(self, substitutes):
        [tree_id] = substitutes
        return RequestInfo(
            message="Tree-db item",
            attributes={"treeId": tree_id},
            labels=[Label.TREE_DB],
        )


scenarios = [
    Logs(),
    GetTreedbItem(),
    Admin(),
    CdnAppsServer(),
    UpdateAssetGtwAsset(),
    PutAssetGtwAccess(),
    PutAssetGtwAsset(),
    GetAssetGtwPackageMetadata(),
    GetCDNPackageMetadata(),
    GetCDNPackage1(),
    GetCDNPackage2(),
    Api(),
    All(),
]


def request_info(request: Request):
    attributes = {}
    labels = []
    message = None
    for scenario in scenarios:
        try:
            info = scenario.extract(request)
            if info:
                attributes = {**attributes, **info.attributes}
                labels = [*labels, *info.labels]

            if info and not message:
                message = info.message
        except Exception:
            tb = traceback.format_exc()
            print("Error occurred trying to extract request info")
            print(tb)

    return RequestInfo(message=message, attributes=attributes, labels=labels)
