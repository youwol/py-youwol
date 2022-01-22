import traceback
from abc import ABC, abstractmethod
from typing import NamedTuple, Dict, List

from starlette.requests import Request

from youwol_utils import decode_id
from youwol_utils.context import Label


class RequestInfoExtractor(ABC):

    @abstractmethod
    def match(self, request: Request):
        return NotImplemented

    @abstractmethod
    def message(self, request: Request):
        return NotImplemented

    @abstractmethod
    def attributes(self, request: Request):
        return NotImplemented

    @abstractmethod
    def labels(self, request: Request):
        return NotImplemented


class All(RequestInfoExtractor):

    def match(self, request: Request):
        return True

    def message(self, request: Request):
        return request.url.path.split('/')[-1]

    def attributes(self, request: Request):
        return {'method': request.method}

    def labels(self, request):
        return []


class Api(RequestInfoExtractor):

    prefix = "/api/"

    def match(self, request: Request):
        return request.url.path.startswith(self.prefix)

    def message(self, request: Request):
        return request.url.path.split('/')[-1]

    def attributes(self, request: Request):
        rest_of_path = request.url.path.split(self.prefix)[1]
        service = rest_of_path.split('/')[0]
        return {'service': service}

    def labels(self, request):
        return []


class Admin(RequestInfoExtractor):

    prefix = "/admin/"

    def match(self, request: Request):
        return request.url.path.startswith(self.prefix)

    def message(self, request: Request):
        return request.url.path.split('/')[-1]

    def attributes(self, request: Request):
        rest_of_path = request.url.path.split(self.prefix)[1]
        service = rest_of_path.split('/')[0]
        return {'router': service}

    def labels(self, request):
        return [Label.ADMIN]


class GetAssetGtwMetadata(RequestInfoExtractor):

    prefix = '/api/assets-gateway/raw/package/metadata/'

    def match(self, request: Request):
        return request.url.path.startswith(self.prefix) and request.method == 'GET'

    def message(self, request: Request):
        return "asset metadata"

    def attributes(self, request: Request):
        asset_id = request.url.path.split(self.prefix)[1].split('/')[0]
        raw_id = decode_id(asset_id)
        return {'assetId': asset_id, 'package': raw_id}

    def labels(self, request):
        return []


class GetPackageMetadata(RequestInfoExtractor):

    prefix = '/api/cdn-backend/libraries/'

    def match(self, request: Request):
        return request.url.path.startswith(self.prefix) and request.method == 'GET'

    def message(self, request: Request):
        return "package metadata"

    def attributes(self, request: Request):
        asset_id = request.url.path.split(self.prefix)[1]
        return {'rawId': asset_id}

    def labels(self, request):
        return []


scenarios = [
    GetAssetGtwMetadata(),
    GetPackageMetadata(),
    Api(),
    All()
]


class RequestInfo(NamedTuple):
    message: str
    attributes: Dict[str, str]
    labels: List[str]


def request_info(request: Request):

    attributes = {}
    labels = []
    message = None
    for scenario in scenarios:

        try:
            if scenario.match(request):
                attributes = {**attributes, **scenario.attributes(request)}
                labels = [*labels, *scenario.labels(request)]

            if scenario.match(request) and not message:
                message = scenario.message(request=request)

        except RuntimeError as e:
            tb = traceback.format_exc()
            request.state.context and request.state.context.error(
                text="Error occurred trying to extract request info",
                data={
                    'error': e.__str__(),
                    'traceback': tb.split('\n'),
                    'args': [arg.__str__() for arg in e.args]
                })
    return RequestInfo(message=message, attributes=attributes, labels=labels)
