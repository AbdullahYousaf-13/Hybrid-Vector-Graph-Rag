import datetime
import os
import threading

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

MAX_REQUESTS_PER_DAY = 250

# Stored as a (:DailyQuota {date, count}) node in Neo4j rather than a local file, so the count
# survives Render redeploys/restarts and is shared by every process using the same database.
QUOTA_LABEL = "DailyQuota"

# Taking a write lock (SET q._lock) before reading q.count stops two concurrent requests from
# both reading the same count and losing an increment; see Neo4j's "lost updates" guidance.
_INCREMENT = f"""
MERGE (q:{QUOTA_LABEL} {{date: $date}})
  ON CREATE SET q.count = 0
SET q._lock = true
WITH q
WHERE q.count < $max
SET q.count = q.count + 1
RETURN q.count AS count
"""

_READ = f"MATCH (q:{QUOTA_LABEL} {{date: $date}}) RETURN q.count AS count"


class QuotaExceededError(RuntimeError):
    """The app's own daily cap was hit (not a Gemini-side limit)."""


def _today() -> str:
    # UTC so a local run and the Render deploy agree on when the day rolls over.
    return datetime.datetime.now(datetime.timezone.utc).date().isoformat()


class Neo4jDailyQuota:
    def __init__(self, max_rpd: int = MAX_REQUESTS_PER_DAY):
        self.max_rpd = max_rpd
        self._driver = None
        self._init_lock = threading.Lock()

    def _db(self):
        with self._init_lock:
            if self._driver is None:
                self._driver = GraphDatabase.driver(
                    os.getenv("NEO4J_URI"),
                    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")),
                )
                # Makes concurrent MERGEs on a new day create one node, not duplicates.
                self._query(
                    f"CREATE CONSTRAINT daily_quota_date IF NOT EXISTS "
                    f"FOR (q:{QUOTA_LABEL}) REQUIRE q.date IS UNIQUE"
                )
        return self._driver

    def _query(self, cypher: str, **params):
        records, _, _ = self._driver.execute_query(
            cypher, params, database_=os.getenv("NEO4J_DATABASE")
        )
        return records

    def check_and_increment(self):
        self._db()
        records = self._query(_INCREMENT, date=_today(), max=self.max_rpd)
        if not records:
            raise QuotaExceededError(
                f"Daily Quota Guardrail Triggered: Max daily limit of {self.max_rpd} "
                f"requests reached ({self.max_rpd}/{self.max_rpd}). Resets at midnight UTC."
            )
        print(f"[Shared Daily Quota] Total requests used today: {records[0]['count']}/{self.max_rpd}")

    def usage(self) -> dict:
        self._db()
        records = self._query(_READ, date=_today())
        return {"used": records[0]["count"] if records else 0, "max": self.max_rpd}


daily_limiter = Neo4jDailyQuota()
