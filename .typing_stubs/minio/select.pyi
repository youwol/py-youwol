# standard library
from abc import ABCMeta
from collections.abc import Generator

# third parties
from _typeshed import Incomplete

# relative
from .error import MinioException as MinioException
from .xml import Element as Element
from .xml import SubElement as SubElement
from .xml import findtext as findtext

COMPRESSION_TYPE_NONE: str
COMPRESSION_TYPE_GZIP: str
COMPRESSION_TYPE_BZIP2: str
FILE_HEADER_INFO_USE: str
FILE_HEADER_INFO_IGNORE: str
FILE_HEADER_INFO_NONE: str
JSON_TYPE_DOCUMENT: str
JSON_TYPE_LINES: str
QUOTE_FIELDS_ALWAYS: str
QUOTE_FIELDS_ASNEEDED: str

class InputSerialization:
    __metaclass__ = ABCMeta
    def __init__(self, compression_type) -> None: ...
    def toxml(self, element): ...

class CSVInputSerialization(InputSerialization):
    def __init__(
        self,
        compression_type: Incomplete | None = ...,
        allow_quoted_record_delimiter: Incomplete | None = ...,
        comments: Incomplete | None = ...,
        field_delimiter: Incomplete | None = ...,
        file_header_info: Incomplete | None = ...,
        quote_character: Incomplete | None = ...,
        quote_escape_character: Incomplete | None = ...,
        record_delimiter: Incomplete | None = ...,
    ) -> None: ...
    def toxml(self, element) -> None: ...

class JSONInputSerialization(InputSerialization):
    def __init__(
        self,
        compression_type: Incomplete | None = ...,
        json_type: Incomplete | None = ...,
    ) -> None: ...
    def toxml(self, element) -> None: ...

class ParquetInputSerialization(InputSerialization):
    def __init__(self) -> None: ...
    def toxml(self, element): ...

class CSVOutputSerialization:
    def __init__(
        self,
        field_delimiter: Incomplete | None = ...,
        quote_character: Incomplete | None = ...,
        quote_escape_character: Incomplete | None = ...,
        quote_fields: Incomplete | None = ...,
        record_delimiter: Incomplete | None = ...,
    ) -> None: ...
    def toxml(self, element) -> None: ...

class JSONOutputSerialization:
    def __init__(self, record_delimiter: Incomplete | None = ...) -> None: ...
    def toxml(self, element) -> None: ...

class SelectRequest:
    def __init__(
        self,
        expression,
        input_serialization,
        output_serialization,
        request_progress: bool = ...,
        scan_start_range: Incomplete | None = ...,
        scan_end_range: Incomplete | None = ...,
    ) -> None: ...
    def toxml(self, element): ...

class Stats:
    def __init__(self, data) -> None: ...
    @property
    def bytes_scanned(self): ...
    @property
    def bytes_processed(self): ...
    @property
    def bytes_returned(self): ...

class SelectObjectReader:
    def __init__(self, response) -> None: ...
    def __enter__(self): ...
    def __exit__(self, exc_type, exc_value, exc_traceback): ...
    def readable(self): ...
    def writeable(self): ...
    def close(self) -> None: ...
    def stats(self): ...
    def stream(self, num_bytes=...) -> Generator[Incomplete, None, None]: ...
