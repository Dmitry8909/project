from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement
from datetime import datetime, timezone


class ScyllaClient:
    def __init__(self, contact_points: str, keyspace: str = "blog"):
        self._contact_points = contact_points.split(",")
        self._keyspace = keyspace
        self._session = None

    def start(self):
        if self._session is not None:
            return
        cluster = Cluster(self._contact_points)
        self._session = cluster.connect()
        self._create_schema()

    def _create_schema(self):
        self._execute(
            f"CREATE KEYSPACE IF NOT EXISTS {self._keyspace} "
            f"WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}}"
        )
        self._execute(f"USE {self._keyspace}")
        self._execute("""
            CREATE TABLE IF NOT EXISTS feed (
                user_id text,
                post_id text,
                author_id text,
                timestamp timestamp,
                PRIMARY KEY (user_id, timestamp, post_id)
            ) WITH CLUSTERING ORDER BY (timestamp DESC, post_id ASC)
        """)
        self._execute("""
            CREATE TABLE IF NOT EXISTS post_likes (
                post_id text,
                user_id text,
                timestamp timestamp,
                PRIMARY KEY (post_id, user_id)
            )
        """)
        self._execute("""
            CREATE TABLE IF NOT EXISTS post_counts (
                post_id text PRIMARY KEY,
                likes_count counter,
                comments_count counter
            )
        """)

    def _execute(self, query: str, params: tuple | None = None):
        stmt = SimpleStatement(query)
        if params:
            self._session.execute(stmt, params)
        else:
            self._session.execute(stmt)

    def insert_feed_entry(self, user_id: str, post_id: str,
                          author_id: str, timestamp: float):
        ts = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        self._execute(
            "INSERT INTO feed (user_id, post_id, author_id, timestamp) VALUES (%s, %s, %s, %s)",
            (user_id, post_id, author_id, ts),
        )

    def get_feed(self, user_id: str, limit: int = 20):
        rows = self._session.execute(
            SimpleStatement(
                "SELECT post_id, author_id, timestamp FROM feed WHERE user_id = %s "
                "ORDER BY timestamp DESC LIMIT %s",
            ),
            (user_id, limit),
        )
        return [{"post_id": r.post_id, "author_id": r.author_id} for r in rows]

    def get_feed_page(self, user_id: str, limit: int = 20,
                      before_timestamp: float | None = None):
        if before_timestamp:
            ts = datetime.fromtimestamp(before_timestamp, tz=timezone.utc)
            rows = self._session.execute(
                SimpleStatement(
                    "SELECT post_id, author_id, timestamp FROM feed "
                    "WHERE user_id = %s AND timestamp < %s "
                    "ORDER BY timestamp DESC LIMIT %s",
                ),
                (user_id, ts, limit),
            )
        else:
            rows = self._session.execute(
                SimpleStatement(
                    "SELECT post_id, author_id, timestamp FROM feed "
                    "WHERE user_id = %s ORDER BY timestamp DESC LIMIT %s",
                ),
                (user_id, limit),
            )
        return [{"post_id": r.post_id, "author_id": r.author_id} for r in rows]

    def close(self):
        if self._session:
            self._session.shutdown()
            self._session = None
