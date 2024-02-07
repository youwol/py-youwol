# typing

# third parties
from cassandra import query
from cassandra.cluster import Cluster, Session


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

    def execute(self, q: str, values: list | None = None):
        return self.cassandra_session.execute(query=q, parameters=values)
