# standard library
import sys

# third parties
import semantic_version

# Youwol
from youwol.integrity.corrections.cql.common import Correction
from youwol.integrity.corrections.cql.replace import Replace
from youwol.integrity.services.cql import CqlSession

# relative
from ...models import LibrariesRow
from .commons import check_owner


def check(session: CqlSession) -> list[Correction]:
    corrections: list[Correction] = []
    for row_data in session.execute(q="SELECT * FROM prod_cdn.libraries"):
        row = LibrariesRow(**row_data)
        r = check_owner(row)
        if r:
            corrections.append(r)
        else:
            r = check_version_number(row)
            if r:
                corrections.append(r)
    return corrections


def check_version_number(row: LibrariesRow) -> Correction | None:
    expected_version_number = _version_number_from_version(row.version)
    actual_version_number = row.version_number
    if actual_version_number != expected_version_number:
        print(
            f"[{row.library_id}] expected=<{expected_version_number}> actual=<{actual_version_number}>"
        )
        new_row = LibrariesRow(
            **{**row.__dict__, "version_number": expected_version_number}
        )
        return Replace(old=row, new=new_row)
    return None


def _version_number_from_version(version: str) -> str:
    delta = 0
    semver = semantic_version.Version(version)
    if semver.prerelease:
        prerelease = semver.prerelease[0]
        # 'next' deprecated: for backward compatibility (10/03/2022)
        delta = (
            1
            if prerelease == "next"
            else -(
                1 + ["wip", "alpha", "alpha-wip", "beta", "beta-wip"].index(prerelease)
            )
        )

    version_number_int = (
        semver.major * 10_000_000 + semver.minor * 10_000 + semver.patch * 10 + delta
    )
    return f"{version_number_int:010d}"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Expect one and only one argument, the cassandra host.")
        sys.exit(1)
    scylla_host = sys.argv[1]
    print(f"Cassandra host: '{scylla_host}'")
    s = CqlSession(scylla_host)
    for correction in check(session=s):
        print(correction)
        # correction.apply(s)
