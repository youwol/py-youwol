from typing import Union, Mapping, List

JSON = Union[str, int, float, bool, None, Mapping[str, 'JSON'], List['JSON']]
