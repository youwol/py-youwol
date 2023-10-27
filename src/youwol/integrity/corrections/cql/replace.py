# relative
from ...models import LibrariesRow
from ...services.cql import CqlSession
from .common import Correction


class Replace(Correction):
    old: LibrariesRow
    new: LibrariesRow

    def __init__(self, old: LibrariesRow, new: LibrariesRow):
        super().__init__()
        self.old = old
        self.new = new

    def apply(self, session: CqlSession):
        print(f"# replace old row '{self.old}' by new row '{self.new}'")
        self.__insert_new(session=session)
        self.__delete_old(session=session)
        print(f"# old row '{self.old}' replaced by new row '{self.new}'")
        print()

    def __insert_new(self, session: CqlSession):
        row = self.new
        columns_clause = "\n , ".join([f"{name}" for name in row.__dict__.keys()])
        values_clause = ", ".join(["%s"] * len(row.__dict__))
        values = [row[name] for name in row.__dict__.keys()]
        ks, table = row.get_keyspace_table()
        query = f"INSERT INTO {ks}.{table}\n ( {columns_clause})\n VALUES ( {values_clause});"
        print(f"# insert new row '{row}'\n{query}")
        print(f"# with values {values}")
        session.execute(q=query, values=values)
        print(f"# new row '{row}' inserted")

    def __delete_old(self, session: CqlSession):
        row = self.old
        where_clause = "\n  AND ".join(
            [f"{name}='{row[name]}'" for name in row.get_key_columns()]
        )
        ks, table = row.get_keyspace_table()
        query = f"DELETE FROM {ks}.{table}\nWHERE {where_clause};"
        print(f"# delete old row '{row}'\n{query}")
        session.execute(q=query)
        print(f"# old row '{row}' deleted")
