# relative
from ...corrections.cql.common import Correction
from ...corrections.cql.replace import Replace
from ...models import LibrariesRow, constants


def check_owner(row: LibrariesRow) -> Correction | None:
    id_ok = row.owner_id == constants.COLUMN_OWNER_ID_VALUE
    name_ok = row.owner_name == constants.COLUMN_OWNER_NAME_VALUE
    kind_ok = row.owner_kind == constants.COLUMN_OWNER_KIND_VALUE
    if not id_ok:
        print(
            f"[{row}] expected_owner_id={constants.COLUMN_OWNER_ID_VALUE} actual_owner_id={row.owner_id}"
        )
    if not name_ok:
        print(
            f"[{row}] expected_owner_name={constants.COLUMN_OWNER_NAME_VALUE} actual_owner_id={row.owner_name}"
        )
    if not kind_ok:
        print(
            f"[{row}] expected_owner_kind={constants.COLUMN_OWNER_KIND_VALUE} actual_owner_id={row.owner_kind}"
        )
    if not id_ok & name_ok & kind_ok:
        return Replace(old=row, new=row)
    return None
