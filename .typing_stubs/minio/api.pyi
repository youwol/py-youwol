# standard library
from collections.abc import Generator

# third parties
from _typeshed import Incomplete

# relative
from . import time as time
from .commonconfig import COPY as COPY
from .commonconfig import REPLACE as REPLACE
from .commonconfig import ComposeSource as ComposeSource
from .commonconfig import CopySource as CopySource
from .commonconfig import Tags as Tags
from .credentials import StaticProvider as StaticProvider
from .datatypes import CompleteMultipartUploadResult as CompleteMultipartUploadResult
from .datatypes import EventIterable as EventIterable
from .datatypes import ListAllMyBucketsResult as ListAllMyBucketsResult
from .datatypes import ListMultipartUploadsResult as ListMultipartUploadsResult
from .datatypes import ListPartsResult as ListPartsResult
from .datatypes import Object as Object
from .datatypes import Part as Part
from .datatypes import PostPolicy as PostPolicy
from .datatypes import parse_copy_object as parse_copy_object
from .datatypes import parse_list_objects as parse_list_objects
from .deleteobjects import DeleteError as DeleteError
from .deleteobjects import DeleteRequest as DeleteRequest
from .deleteobjects import DeleteResult as DeleteResult
from .error import InvalidResponseError as InvalidResponseError
from .error import S3Error as S3Error
from .error import ServerError as ServerError
from .helpers import MAX_MULTIPART_COUNT as MAX_MULTIPART_COUNT
from .helpers import MAX_MULTIPART_OBJECT_SIZE as MAX_MULTIPART_OBJECT_SIZE
from .helpers import MAX_PART_SIZE as MAX_PART_SIZE
from .helpers import MIN_PART_SIZE as MIN_PART_SIZE
from .helpers import BaseURL as BaseURL
from .helpers import ObjectWriteResult as ObjectWriteResult
from .helpers import ThreadPool as ThreadPool
from .helpers import check_bucket_name as check_bucket_name
from .helpers import check_non_empty_string as check_non_empty_string
from .helpers import check_sse as check_sse
from .helpers import check_ssec as check_ssec
from .helpers import genheaders as genheaders
from .helpers import get_part_info as get_part_info
from .helpers import headers_to_strings as headers_to_strings
from .helpers import is_valid_policy_type as is_valid_policy_type
from .helpers import makedirs as makedirs
from .helpers import md5sum_hash as md5sum_hash
from .helpers import read_part_data as read_part_data
from .helpers import sha256_hash as sha256_hash
from .legalhold import LegalHold as LegalHold
from .lifecycleconfig import LifecycleConfig as LifecycleConfig
from .notificationconfig import NotificationConfig as NotificationConfig
from .objectlockconfig import ObjectLockConfig as ObjectLockConfig
from .replicationconfig import ReplicationConfig as ReplicationConfig
from .retention import Retention as Retention
from .select import SelectObjectReader as SelectObjectReader
from .select import SelectRequest as SelectRequest
from .signer import presign_v4 as presign_v4
from .signer import sign_v4_s3 as sign_v4_s3
from .sse import SseCustomerKey as SseCustomerKey
from .sseconfig import SSEConfig as SSEConfig
from .tagging import Tagging as Tagging
from .versioningconfig import VersioningConfig as VersioningConfig
from .xml import Element as Element
from .xml import SubElement as SubElement
from .xml import findtext as findtext
from .xml import getbytes as getbytes
from .xml import marshal as marshal
from .xml import unmarshal as unmarshal

class Minio:
    def __init__(
        self,
        endpoint,
        access_key: Incomplete | None = ...,
        secret_key: Incomplete | None = ...,
        session_token: Incomplete | None = ...,
        secure: bool = ...,
        region: Incomplete | None = ...,
        http_client: Incomplete | None = ...,
        credentials: Incomplete | None = ...,
    ) -> None: ...
    def __del__(self) -> None: ...
    def set_app_info(self, app_name, app_version) -> None: ...
    def trace_on(self, stream) -> None: ...
    def trace_off(self) -> None: ...
    def enable_accelerate_endpoint(self) -> None: ...
    def disable_accelerate_endpoint(self) -> None: ...
    def enable_dualstack_endpoint(self) -> None: ...
    def disable_dualstack_endpoint(self) -> None: ...
    def enable_virtual_style_endpoint(self) -> None: ...
    def disable_virtual_style_endpoint(self) -> None: ...
    def select_object_content(self, bucket_name, object_name, request): ...
    def make_bucket(
        self, bucket_name, location: Incomplete | None = ..., object_lock: bool = ...
    ) -> None: ...
    def list_buckets(self): ...
    def bucket_exists(self, bucket_name): ...
    def remove_bucket(self, bucket_name) -> None: ...
    def get_bucket_policy(self, bucket_name): ...
    def delete_bucket_policy(self, bucket_name) -> None: ...
    def set_bucket_policy(self, bucket_name, policy) -> None: ...
    def get_bucket_notification(self, bucket_name): ...
    def set_bucket_notification(self, bucket_name, config) -> None: ...
    def delete_bucket_notification(self, bucket_name) -> None: ...
    def set_bucket_encryption(self, bucket_name, config) -> None: ...
    def get_bucket_encryption(self, bucket_name): ...
    def delete_bucket_encryption(self, bucket_name) -> None: ...
    def listen_bucket_notification(
        self, bucket_name, prefix: str = ..., suffix: str = ..., events=...
    ): ...
    def set_bucket_versioning(self, bucket_name, config) -> None: ...
    def get_bucket_versioning(self, bucket_name): ...
    def fput_object(
        self,
        bucket_name,
        object_name,
        file_path,
        content_type: str = ...,
        metadata: Incomplete | None = ...,
        sse: Incomplete | None = ...,
        progress: Incomplete | None = ...,
        part_size: int = ...,
        num_parallel_uploads: int = ...,
        tags: Incomplete | None = ...,
        retention: Incomplete | None = ...,
        legal_hold: bool = ...,
    ): ...
    def fget_object(
        self,
        bucket_name,
        object_name,
        file_path,
        request_headers: Incomplete | None = ...,
        ssec: Incomplete | None = ...,
        version_id: Incomplete | None = ...,
        extra_query_params: Incomplete | None = ...,
        tmp_file_path: Incomplete | None = ...,
    ): ...
    def get_object(
        self,
        bucket_name,
        object_name,
        offset: int = ...,
        length: int = ...,
        request_headers: Incomplete | None = ...,
        ssec: Incomplete | None = ...,
        version_id: Incomplete | None = ...,
        extra_query_params: Incomplete | None = ...,
    ): ...
    def copy_object(
        self,
        bucket_name,
        object_name,
        source,
        sse: Incomplete | None = ...,
        metadata: Incomplete | None = ...,
        tags: Incomplete | None = ...,
        retention: Incomplete | None = ...,
        legal_hold: bool = ...,
        metadata_directive: Incomplete | None = ...,
        tagging_directive: Incomplete | None = ...,
    ): ...
    def compose_object(
        self,
        bucket_name,
        object_name,
        sources,
        sse: Incomplete | None = ...,
        metadata: Incomplete | None = ...,
        tags: Incomplete | None = ...,
        retention: Incomplete | None = ...,
        legal_hold: bool = ...,
    ): ...
    def put_object(
        self,
        bucket_name,
        object_name,
        data,
        length,
        content_type: str = ...,
        metadata: Incomplete | None = ...,
        sse: Incomplete | None = ...,
        progress: Incomplete | None = ...,
        part_size: int = ...,
        num_parallel_uploads: int = ...,
        tags: Incomplete | None = ...,
        retention: Incomplete | None = ...,
        legal_hold: bool = ...,
    ): ...
    def list_objects(
        self,
        bucket_name,
        prefix: Incomplete | None = ...,
        recursive: bool = ...,
        start_after: Incomplete | None = ...,
        include_user_meta: bool = ...,
        include_version: bool = ...,
        use_api_v1: bool = ...,
        use_url_encoding_type: bool = ...,
    ): ...
    def stat_object(
        self,
        bucket_name,
        object_name,
        ssec: Incomplete | None = ...,
        version_id: Incomplete | None = ...,
        extra_query_params: Incomplete | None = ...,
    ): ...
    def remove_object(
        self, bucket_name, object_name, version_id: Incomplete | None = ...
    ) -> None: ...
    def remove_objects(
        self, bucket_name, delete_object_list, bypass_governance_mode: bool = ...
    ) -> Generator[Incomplete, None, None]: ...
    def get_presigned_url(
        self,
        method,
        bucket_name,
        object_name,
        expires=...,
        response_headers: Incomplete | None = ...,
        request_date: Incomplete | None = ...,
        version_id: Incomplete | None = ...,
        extra_query_params: Incomplete | None = ...,
    ): ...
    def presigned_get_object(
        self,
        bucket_name,
        object_name,
        expires=...,
        response_headers: Incomplete | None = ...,
        request_date: Incomplete | None = ...,
        version_id: Incomplete | None = ...,
        extra_query_params: Incomplete | None = ...,
    ): ...
    def presigned_put_object(self, bucket_name, object_name, expires=...): ...
    def presigned_post_policy(self, policy): ...
    def delete_bucket_replication(self, bucket_name) -> None: ...
    def get_bucket_replication(self, bucket_name): ...
    def set_bucket_replication(self, bucket_name, config) -> None: ...
    def delete_bucket_lifecycle(self, bucket_name) -> None: ...
    def get_bucket_lifecycle(self, bucket_name): ...
    def set_bucket_lifecycle(self, bucket_name, config) -> None: ...
    def delete_bucket_tags(self, bucket_name) -> None: ...
    def get_bucket_tags(self, bucket_name): ...
    def set_bucket_tags(self, bucket_name, tags) -> None: ...
    def delete_object_tags(
        self, bucket_name, object_name, version_id: Incomplete | None = ...
    ) -> None: ...
    def get_object_tags(
        self, bucket_name, object_name, version_id: Incomplete | None = ...
    ): ...
    def set_object_tags(
        self, bucket_name, object_name, tags, version_id: Incomplete | None = ...
    ) -> None: ...
    def enable_object_legal_hold(
        self, bucket_name, object_name, version_id: Incomplete | None = ...
    ) -> None: ...
    def disable_object_legal_hold(
        self, bucket_name, object_name, version_id: Incomplete | None = ...
    ) -> None: ...
    def is_object_legal_hold_enabled(
        self, bucket_name, object_name, version_id: Incomplete | None = ...
    ): ...
    def delete_object_lock_config(self, bucket_name) -> None: ...
    def get_object_lock_config(self, bucket_name): ...
    def set_object_lock_config(self, bucket_name, config) -> None: ...
    def get_object_retention(
        self, bucket_name, object_name, version_id: Incomplete | None = ...
    ): ...
    def set_object_retention(
        self, bucket_name, object_name, config, version_id: Incomplete | None = ...
    ) -> None: ...
