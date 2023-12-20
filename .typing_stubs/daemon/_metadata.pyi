# third parties
from _typeshed import Incomplete

__metaclass__ = type
distribution_name: str
version_info_filename: str

def get_distribution(name): ...
def get_distribution_version_info(distribution, filename=...): ...

distribution: Incomplete
version_info: Incomplete
version_installed: Incomplete
author_name: str
author_email: str
author: Incomplete

class YearRange:
    begin: Incomplete
    end: Incomplete
    def __init__(self, begin, end: Incomplete | None = ...) -> None: ...
    def __unicode__(self): ...

def make_year_range(begin_year, end_date: Incomplete | None = ...): ...

copyright_year_begin: str
build_date: Incomplete
copyright_year_range: Incomplete
copyright: Incomplete
license: str
url: str
