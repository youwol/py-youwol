# typing
from typing import Optional

# third parties
from cassandra import query  # pylint: disable=import-error
from cassandra.cluster import Cluster, Session  # pylint: disable=import-error


class CqlSession:
    hosts: list[str]
    cassandra_session: Session

    def __init__(self, hosts: str | list[str]):
        self.hosts = [hosts] if isinstance(hosts, str) else hosts
        cluster = Cluster(self.hosts)
        self.cassandra_session = cluster.connect()
        self.cassandra_session.row_factory = query.dict_factory

    def prepare(self, keyspace: str, q: str):
        return self.cassandra_session.prepare(keyspace=keyspace, query=q)

    def execute(self, q: str, values: Optional[list] = None):
        return self.cassandra_session.execute(query=q, parameters=values)
