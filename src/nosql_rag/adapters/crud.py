"""Native Python adapters for Redis, MongoDB, Apache Cassandra, and Neo4j."""

from __future__ import annotations

import json
import ssl
import time
from typing import Any

from nosql_rag.adapters.base import AdapterError, BaseCRUDAdapter, safe_identifier
from nosql_rag.config import DatabaseConfig


class RedisAdapter(BaseCRUDAdapter):
    """Redis key-value adapter using redis-py."""

    name = "Redis"

    def __init__(self, url: str) -> None:
        import redis

        self.client = redis.Redis.from_url(
            url, decode_responses=True, socket_timeout=10, socket_connect_timeout=10
        )

    def check(self) -> bool:
        ok = bool(self.client.ping())
        info = self.client.info("server")
        self.version = str(info.get("redis_version", "unknown"))
        return ok

    def metadata(self) -> dict[str, Any]:
        return {"database": self.name, "version": self.version, "model": "key_value"}

    def prepare(self, run_id: str, records: list[dict[str, str]]) -> None:
        prefix = f"nosql_research:{run_id}"
        pipe = self.client.pipeline(transaction=False)
        for row in records:
            pipe.set(f"{prefix}:{row['record_id']}", row["payload_json"])
        pipe.execute()

    def read(self, run_id: str, record_id: str) -> bool:
        return self.client.get(f"nosql_research:{run_id}:{record_id}") is not None

    def update(self, run_id: str, record_id: str, payload_json: str) -> bool:
        return bool(self.client.set(f"nosql_research:{run_id}:{record_id}", payload_json))

    def cleanup(self, run_id: str) -> None:
        prefix = f"nosql_research:{run_id}:"
        keys = list(self.client.scan_iter(match=prefix + "*", count=500))
        if keys:
            self.client.delete(*keys)

    def close(self) -> None:
        self.client.close()


class MongoAdapter(BaseCRUDAdapter):
    """MongoDB document adapter using pymongo."""

    name = "MongoDB"

    def __init__(self, uri: str, database: str = "nosql_rag_research") -> None:
        from pymongo import MongoClient

        self.client = MongoClient(uri, serverSelectionTimeoutMS=10000, connectTimeoutMS=10000)
        self.db = self.client[database]

    def check(self) -> bool:
        info = self.client.admin.command("buildInfo")
        self.version = str(info.get("version", "unknown"))
        self.client.admin.command("ping")
        return True

    def metadata(self) -> dict[str, Any]:
        return {"database": self.name, "version": self.version, "model": "document"}

    def _collection(self, run_id: str) -> Any:
        return self.db[safe_identifier(f"bench_{run_id}")]

    def prepare(self, run_id: str, records: list[dict[str, str]]) -> None:
        coll = self._collection(run_id)
        if records:
            docs = [
                {
                    "_id": str(row["record_id"]),
                    "payload": json.loads(row["payload_json"]),
                    "run_id": run_id,
                }
                for row in records
            ]
            coll.insert_many(docs, ordered=False)

    def read(self, run_id: str, record_id: str) -> bool:
        return self._collection(run_id).find_one({"_id": str(record_id)}, {"_id": 1}) is not None

    def update(self, run_id: str, record_id: str, payload_json: str) -> bool:
        result = self._collection(run_id).update_one(
            {"_id": str(record_id)}, {"$set": {"payload": json.loads(payload_json)}}
        )
        return result.matched_count == 1

    def cleanup(self, run_id: str) -> None:
        self.db.drop_collection(safe_identifier(f"bench_{run_id}"))

    def close(self) -> None:
        self.client.close()


class CassandraAdapter(BaseCRUDAdapter):
    """Apache Cassandra wide-column adapter using cassandra-driver."""

    name = "Cassandra"

    def __init__(
        self,
        hosts: str,
        port: int = 9042,
        username: str | None = None,
        password: str | None = None,
        keyspace: str | None = None,
        use_ssl: bool = False,
    ) -> None:
        try:
            from cassandra.auth import PlainTextAuthProvider
            from cassandra.cluster import Cluster
        except ImportError as exc:
            raise AdapterError("cassandra-driver is not installed in this runtime") from exc

        if not hosts or not keyspace:
            raise AdapterError("Cassandra requires CASSANDRA_HOSTS and CASSANDRA_KEYSPACE")

        host_list = [h.strip() for h in hosts.split(",") if h.strip()]
        auth = PlainTextAuthProvider(username=username, password=password) if username else None
        ssl_context = ssl.create_default_context() if use_ssl else None
        self.cluster = Cluster(
            contact_points=host_list,
            port=int(port),
            auth_provider=auth,
            ssl_context=ssl_context,
            connect_timeout=10,
        )
        self.session = self.cluster.connect(keyspace)
        self.keyspace = keyspace
        self.prepared: dict[str, dict[str, Any]] = {}

    def check(self) -> bool:
        row = self.session.execute("SELECT release_version FROM system.local").one()
        self.version = str(row.release_version) if row else "unknown"
        return row is not None

    def metadata(self) -> dict[str, Any]:
        return {"database": self.name, "version": self.version, "model": "wide_column"}

    def _table(self, run_id: str) -> str:
        return safe_identifier(f"bench_{run_id}")

    def prepare(self, run_id: str, records: list[dict[str, str]]) -> None:
        table = self._table(run_id)
        self.session.execute(
            f"CREATE TABLE IF NOT EXISTS {table} (record_id text PRIMARY KEY, payload_json text)"
        )
        insert_stmt = self.session.prepare(
            f"INSERT INTO {table} (record_id, payload_json) VALUES (?, ?)"
        )
        for row in records:
            self.session.execute(insert_stmt, (str(row["record_id"]), row["payload_json"]))
        self.prepared[run_id] = {
            "table": table,
            "select": self.session.prepare(f"SELECT record_id FROM {table} WHERE record_id = ?"),
            "update": self.session.prepare(
                f"UPDATE {table} SET payload_json = ? WHERE record_id = ?"
            ),
        }

    def read(self, run_id: str, record_id: str) -> bool:
        result = self.session.execute(self.prepared[run_id]["select"], (str(record_id),)).one()
        return result is not None

    def update(self, run_id: str, record_id: str, payload_json: str) -> bool:
        self.session.execute(self.prepared[run_id]["update"], (payload_json, str(record_id)))
        return True

    def cleanup(self, run_id: str) -> None:
        item = self.prepared.pop(run_id, None)
        table = item["table"] if item else self._table(run_id)
        self.session.execute(f"DROP TABLE IF EXISTS {table}")

    def close(self) -> None:
        self.cluster.shutdown()


class Neo4jAdapter(BaseCRUDAdapter):
    """Neo4j property-graph adapter supporting both indexed CRUD and graph traversal."""

    name = "Neo4j"

    def __init__(self, uri: str, username: str, password: str, database: str = "neo4j") -> None:
        from neo4j import GraphDatabase

        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        self.database = database or None

    def _session(self) -> Any:
        return (
            self.driver.session(database=self.database) if self.database else self.driver.session()
        )

    def check(self) -> bool:
        self.driver.verify_connectivity()
        with self._session() as session:
            result = session.run(
                "CALL dbms.components() YIELD versions RETURN versions[0] AS version"
            ).single()
            self.version = str(result["version"]) if result else "unknown"
        return True

    def metadata(self) -> dict[str, Any]:
        return {"database": self.name, "version": self.version, "model": "graph"}

    def prepare(self, run_id: str, records: list[dict[str, str]]) -> None:
        with self._session() as session:
            session.run(
                "CREATE INDEX bench_record_run_id IF NOT EXISTS "
                "FOR (n:BenchRecord) ON (n.run_id, n.record_id)"
            ).consume()
            rows = [
                {"record_id": str(x["record_id"]), "payload_json": x["payload_json"]}
                for x in records
            ]
            session.run(
                "UNWIND $rows AS row "
                "MERGE (n:BenchRecord {run_id: $run_id, record_id: row.record_id}) "
                "SET n.payload_json = row.payload_json",
                run_id=run_id,
                rows=rows,
            ).consume()

    def prepare_graph_edges(self, run_id: str, edges: list[tuple[str, str]]) -> None:
        """Create directed :LINKS_TO relationships for native graph traversal benchmarks."""
        with self._session() as session:
            rows = [{"src": str(s), "dst": str(d)} for s, d in edges]
            session.run(
                "UNWIND $rows AS row "
                "MATCH (a:BenchRecord {run_id: $run_id, record_id: row.src}) "
                "MATCH (b:BenchRecord {run_id: $run_id, record_id: row.dst}) "
                "MERGE (a)-[:LINKS_TO]->(b)",
                run_id=run_id,
                rows=rows,
            ).consume()

    def traverse_neighbors(self, run_id: str, record_id: str, depth: int = 2) -> int:
        """Execute a native variable-length k-hop graph traversal."""
        hops = max(1, min(int(depth), 4))
        query = (
            f"MATCH (n:BenchRecord {{run_id: $run_id, record_id: $record_id}})"
            f"-[:LINKS_TO*1..{hops}]->(m:BenchRecord) "
            "RETURN count(DISTINCT m) AS reached"
        )
        with self._session() as session:
            result = session.run(query, run_id=run_id, record_id=str(record_id)).single()
            return int(result["reached"]) if result else 0

    def read(self, run_id: str, record_id: str) -> bool:
        with self._session() as session:
            result = session.run(
                "MATCH (n:BenchRecord {run_id: $run_id, record_id: $record_id}) "
                "RETURN n.record_id AS id LIMIT 1",
                run_id=run_id,
                record_id=str(record_id),
            ).single()
            return result is not None

    def update(self, run_id: str, record_id: str, payload_json: str) -> bool:
        with self._session() as session:
            result = session.run(
                "MATCH (n:BenchRecord {run_id: $run_id, record_id: $record_id}) "
                "SET n.payload_json = $payload_json RETURN count(n) AS changed",
                run_id=run_id,
                record_id=str(record_id),
                payload_json=payload_json,
            ).single()
            return bool(result and result["changed"] == 1)

    def cleanup(self, run_id: str) -> None:
        with self._session() as session:
            session.run("MATCH (n:BenchRecord {run_id: $run_id}) DETACH DELETE n", run_id=run_id).consume()

    def close(self) -> None:
        self.driver.close()


def build_crud_adapter(database_name: str, config: DatabaseConfig) -> BaseCRUDAdapter:
    """Factory returning a configured CRUD adapter for `database_name`."""
    if database_name == "Redis":
        if not config.redis_url:
            raise AdapterError("REDIS_URL is not configured")
        return RedisAdapter(config.redis_url)
    if database_name == "MongoDB":
        if not config.mongodb_uri:
            raise AdapterError("MONGODB_URI is not configured")
        return MongoAdapter(config.mongodb_uri, config.mongodb_database)
    if database_name == "Cassandra":
        if not config.cassandra_hosts or not config.cassandra_keyspace:
            raise AdapterError("CASSANDRA_HOSTS and CASSANDRA_KEYSPACE are required")
        return CassandraAdapter(
            hosts=config.cassandra_hosts,
            port=config.cassandra_port,
            username=config.cassandra_username,
            password=config.cassandra_password,
            keyspace=config.cassandra_keyspace,
            use_ssl=config.cassandra_ssl,
        )
    if database_name == "Neo4j":
        if not all([config.neo4j_uri, config.neo4j_username, config.neo4j_password]):
            raise AdapterError("NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD are required")
        return Neo4jAdapter(
            uri=config.neo4j_uri or "",
            username=config.neo4j_username or "",
            password=config.neo4j_password or "",
            database=config.neo4j_database,
        )
    raise ValueError(f"Unknown CRUD database: {database_name}")


def check_crud_connections(
    config: DatabaseConfig, databases: tuple[str, ...] = ("Redis", "MongoDB", "Cassandra", "Neo4j")
) -> list[dict[str, Any]]:
    """Verify live connectivity for each configured CRUD database without faking success."""
    results: list[dict[str, Any]] = []
    for name in databases:
        adapter: BaseCRUDAdapter | None = None
        started = time.perf_counter()
        try:
            adapter = build_crud_adapter(name, config)
            ok = adapter.check()
            results.append(
                {
                    "database": name,
                    "connected": bool(ok),
                    "version": adapter.version,
                    "connect_check_ms": round((time.perf_counter() - started) * 1000, 3),
                    "error": None,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "database": name,
                    "connected": False,
                    "version": None,
                    "connect_check_ms": round((time.perf_counter() - started) * 1000, 3),
                    "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                }
            )
        finally:
            if adapter is not None:
                try:
                    adapter.close()
                except Exception:
                    pass
    return results
