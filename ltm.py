"""Small, dependency-free governed LTM prototype for the DIT 716 Module 2 demo.

The vector representation is a deterministic signed feature hash, not a trained
semantic embedding. SQLite stores canonical episode summaries and their vectors.
This is a teaching prototype, not a production security boundary.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

DIMENSIONS = 384
TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
STOPWORDS = {"a", "an", "and", "at", "by", "for", "from", "in", "is", "of", "on", "or", "the", "to", "with"}


def embed(text: str) -> list[float]:
    """Create a stable hashed bag-of-words/bigrams vector with signed bins."""
    words = [w.lower() for w in TOKEN_RE.findall(text) if w.lower() not in STOPWORDS]
    features = words + [f"{a}_{b}" for a, b in zip(words, words[1:])]
    vector = [0.0] * DIMENSIONS
    for feature in features:
        digest = hashlib.sha256(feature.encode("utf-8")).digest()
        slot = int.from_bytes(digest[:4], "big") % DIMENSIONS
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[slot] += sign
    norm = math.sqrt(sum(x * x for x in vector))
    return [x / norm for x in vector] if norm else vector


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


@dataclass(frozen=True)
class RetrievalRequest:
    text: str
    role: str = "A3"
    basin: str = "BASIN-1"
    station: str = "S17"
    query_day: int = 365
    observation_day: int = 365
    split: str = "train"
    snapshot_id: str = "dit716-ltm-pilot-v1"
    top_k: int = 1
    max_age_days: int | None = None
    allowed_types: tuple[str, ...] = ("episodic", "semantic", "knowledge_base")


class MemoryGateway:
    """Authoritative record store plus derived vector index and audit events."""

    def __init__(self, db_path: str | Path = ":memory:"):
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._schema()

    def close(self) -> None:
        self.conn.close()

    def _schema(self) -> None:
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS sources(
            source_id TEXT PRIMARY KEY, kind TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active'
        );
        CREATE TABLE IF NOT EXISTS evidence_records(
            evidence_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(source_id)
        );
        CREATE TABLE IF NOT EXISTS episodes(
            memory_id TEXT PRIMARY KEY, memory_type TEXT NOT NULL, station TEXT NOT NULL,
            basin TEXT NOT NULL, summary TEXT NOT NULL, source_ids TEXT NOT NULL,
            evidence_ids TEXT NOT NULL, allowed_roles TEXT NOT NULL, split TEXT NOT NULL,
            snapshot_id TEXT NOT NULL, status TEXT NOT NULL, provenance TEXT NOT NULL,
            approved_day INTEGER NOT NULL, available_day INTEGER NOT NULL,
            valid_from_day INTEGER NOT NULL, valid_to_day INTEGER NOT NULL,
            review_due_day INTEGER, retain_until_day INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS vectors(
            memory_id TEXT PRIMARY KEY REFERENCES episodes(memory_id), vector_json TEXT NOT NULL,
            embedding_version TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit(
            event_id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL,
            actor TEXT NOT NULL, memory_id TEXT, source_id TEXT,
            details_json TEXT NOT NULL, at_monotonic REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS episodes_scope ON episodes(status, basin, station, split, memory_type);
        CREATE INDEX IF NOT EXISTS source_status ON sources(status);
        """)
        self.conn.commit()

    def _audit(self, event: str, actor: str, memory_id: str | None = None,
               source_id: str | None = None, details: dict[str, Any] | None = None) -> None:
        # Store identifiers and decisions, not query or evidence text.
        self.conn.execute(
            "INSERT INTO audit(event,actor,memory_id,source_id,details_json,at_monotonic) VALUES(?,?,?,?,?,?)",
            (event, actor, memory_id, source_id, json.dumps(details or {}, sort_keys=True), time.monotonic()),
        )

    def seed(self, fixture: dict[str, Any]) -> None:
        """Load the frozen synthetic corpus once; reject incompatible snapshots."""
        if self.conn.execute("SELECT 1 FROM episodes LIMIT 1").fetchone():
            existing = {r[0] for r in self.conn.execute("SELECT DISTINCT snapshot_id FROM episodes")}
            if existing != {fixture["snapshot_id"]}:
                raise ValueError("Database already contains a different corpus snapshot; use a new DB")
            return
        with self.conn:
            for source in fixture["sources"]:
                self.conn.execute("INSERT INTO sources(source_id,kind,status) VALUES(?,?,?)",
                                  (source["source_id"], source["kind"], source.get("status", "active")))
            for row in fixture["episodes"]:
                for evidence_id in row["evidence_ids"]:
                    if row["source_ids"]:
                        self.conn.execute("INSERT OR IGNORE INTO evidence_records(evidence_id,source_id) VALUES(?,?)",
                                          (evidence_id, row["source_ids"][0]))
                age = int(row.get("approved_age_days", 0))
                status = row.get("status", "approved")
                approved_day = fixture["decision_day"] - age
                episode = (
                    row["memory_id"], row.get("memory_type", "episodic"), row["station"], row["basin"],
                    row["summary"], json.dumps(row["source_ids"]), json.dumps(row["evidence_ids"]),
                    json.dumps(row["allowed_roles"]), row.get("split", "train"), fixture["snapshot_id"],
                    status, "synthetic", approved_day, int(row.get("available_day", approved_day)),
                    int(row.get("valid_from_day", 0)), int(row.get("valid_to_day", 999999)),
                    row.get("review_due_day"), int(row.get("retain_until_day", approved_day + 365)),
                )
                self.conn.execute("""INSERT INTO episodes VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", episode)
                # Profile values are exact user-scoped fields; never embed them.
                if status == "approved" and row.get("memory_type", "episodic") != "profile":
                    self.conn.execute("INSERT INTO vectors VALUES(?,?,?)",
                                      (row["memory_id"], json.dumps(embed(row["summary"])), "hashbow-384-v1"))
            self._audit("seed_snapshot", "system", details={"snapshot_id": fixture["snapshot_id"],
                                                               "episode_count": len(fixture["episodes"])})

    def propose_summary(self, *, memory_id: str, station: str, basin: str,
                        observed_morphology: str, candidate_hypothesis: str,
                        source_ids: Iterable[str], evidence_ids: Iterable[str],
                        producer_role: str = "A3", split: str = "train",
                        snapshot_id: str = "dit716-ltm-pilot-v1", day: int = 365) -> str:
        """Make a source-linked pending summary; proposal never enters vector search."""
        if producer_role not in {"A1", "A2", "A3", "A4"}:
            raise PermissionError("Only diagnostic agent roles may propose episode summaries")
        source_ids, evidence_ids = sorted(set(source_ids)), sorted(set(evidence_ids))
        if not source_ids or not evidence_ids:
            raise ValueError("A summary needs at least one source and evidence ID")
        placeholders = ",".join("?" for _ in source_ids)
        found = {r[0] for r in self.conn.execute(
            f"SELECT source_id FROM sources WHERE status='active' AND source_id IN ({placeholders})", source_ids)}
        if found != set(source_ids):
            raise ValueError("Every summary source must exist and be active")
        evidence_marks = ",".join("?" for _ in evidence_ids)
        evidence_rows = self.conn.execute(
            f"SELECT evidence_id,source_id FROM evidence_records WHERE evidence_id IN ({evidence_marks})", evidence_ids
        ).fetchall()
        if {r["evidence_id"] for r in evidence_rows} != set(evidence_ids):
            raise ValueError("Every cited evidence ID must exist in the evidence ledger")
        if any(r["source_id"] not in source_ids for r in evidence_rows):
            raise ValueError("Cited evidence must descend from a declared summary source")
        summary = (
            f"At {station}, observed morphology: {observed_morphology}. "
            f"Candidate hypothesis (not an adjudicated outcome): {candidate_hypothesis}. "
            f"Source IDs: {', '.join(source_ids)}. Evidence IDs: {', '.join(evidence_ids)}. "
            "Status: pending human review."
        )
        with self.conn:
            self.conn.execute("""INSERT INTO episodes VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                              (memory_id, "episodic", station, basin, summary, json.dumps(source_ids),
                               json.dumps(evidence_ids), json.dumps(["A1", "A2", "A3", "A4"]), split,
                               snapshot_id, "pending", "synthetic", day, day, 0, 999999, None, day + 365))
            self._audit("summary_proposed", producer_role, memory_id, details={"evidence_ids": evidence_ids})
        return summary

    def approve_episode(self, memory_id: str, *, reviewer_id: str, reviewer_role: str,
                        day: int = 365) -> None:
        if reviewer_role not in {"reviewer", "steward"}:
            raise PermissionError("Only a reviewer/steward can approve an episode")
        row = self.conn.execute("SELECT * FROM episodes WHERE memory_id=?", (memory_id,)).fetchone()
        if row is None or row["status"] != "pending":
            raise ValueError("Only an existing pending episode can be approved")
        source_ids = json.loads(row["source_ids"])
        for source_id in source_ids:
            status = self.conn.execute("SELECT status FROM sources WHERE source_id=?", (source_id,)).fetchone()
            if status is None or status[0] != "active":
                raise ValueError("Cannot approve a summary with missing or revoked sources")
        with self.conn:
            self.conn.execute("UPDATE episodes SET status='approved',approved_day=? WHERE memory_id=?", (day, memory_id))
            self.conn.execute("INSERT OR REPLACE INTO vectors VALUES(?,?,?)",
                              (memory_id, json.dumps(embed(row["summary"])), "hashbow-384-v1"))
            self._audit("episode_approved", reviewer_id, memory_id,
                        details={"reviewer_role": reviewer_role, "source_ids": source_ids})

    def _eligible(self, request: RetrievalRequest) -> tuple[list[sqlite3.Row], dict[str, int]]:
        rows = self.conn.execute("""SELECT e.* FROM episodes e
             WHERE e.status='approved' AND e.basin=? AND e.station=? AND e.split=?
               AND e.snapshot_id=? AND e.memory_type IN (%s)""" %
             ",".join("?" for _ in request.allowed_types),
             (request.basin, request.station, request.split, request.snapshot_id, *request.allowed_types)).fetchall()
        eligible, excluded = [], {"not_yet_available": 0, "not_yet_approved": 0,
                                  "invalid_time": 0, "overdue_review": 0, "expired_ttl": 0,
                                  "revoked_source": 0, "wrong_role": 0, "missing_vector": 0,
                                  "type_not_implemented": 0}
        for row in rows:
            # Profile memory needs an authenticated user identity, which this
            # single-user teaching prototype deliberately does not implement.
            if row["memory_type"] == "profile":
                excluded["type_not_implemented"] += 1; continue
            if row["available_day"] > request.query_day:
                excluded["not_yet_available"] += 1; continue
            if row["approved_day"] > request.query_day:
                excluded["not_yet_approved"] += 1; continue
            if not (row["valid_from_day"] <= request.observation_day <= row["valid_to_day"]):
                excluded["invalid_time"] += 1; continue
            if row["review_due_day"] is not None and row["review_due_day"] < request.query_day:
                excluded["overdue_review"] += 1; continue
            if request.max_age_days is not None and request.query_day - row["approved_day"] > request.max_age_days:
                excluded["expired_ttl"] += 1; continue
            if request.role not in json.loads(row["allowed_roles"]):
                excluded["wrong_role"] += 1; continue
            source_ids = json.loads(row["source_ids"])
            if source_ids:
                marks = ",".join("?" for _ in source_ids)
                active = {r[0] for r in self.conn.execute(
                    f"SELECT source_id FROM sources WHERE status='active' AND source_id IN ({marks})", source_ids)}
                if active != set(source_ids):
                    excluded["revoked_source"] += 1; continue
            eligible.append(row)
        return eligible, excluded

    def retrieve(self, request: RetrievalRequest) -> dict[str, Any]:
        started = time.perf_counter()
        rows, excluded = self._eligible(request)
        qv = embed(request.text)
        scored = []
        for row in rows:
            vector_row = self.conn.execute("SELECT vector_json FROM vectors WHERE memory_id=?", (row["memory_id"],)).fetchone()
            if vector_row is None:
                excluded["missing_vector"] += 1
                continue
            scored.append((cosine(qv, json.loads(vector_row["vector_json"])), row))
        scored.sort(key=lambda x: (-x[0], x[1]["memory_id"]))
        results = []
        for score, row in scored[:request.top_k]:
            results.append({"memory_id": row["memory_id"], "memory_type": row["memory_type"],
                            "summary": row["summary"], "source_ids": json.loads(row["source_ids"]),
                            "evidence_ids": json.loads(row["evidence_ids"]), "status": row["status"],
                            "provenance": row["provenance"], "similarity": round(score, 4)})
        elapsed_ms = (time.perf_counter() - started) * 1000
        query_hash = hashlib.sha256(request.text.encode()).hexdigest()[:16]
        self._audit("retrieve", request.role, details={"query_hash": query_hash,
                      "returned_ids": [r["memory_id"] for r in results], "excluded": excluded,
                      "latency_ms": round(elapsed_ms, 4)})
        self.conn.commit()
        return {"items": results, "excluded": excluded, "latency_ms": elapsed_ms,
                "context_tokens_estimate": sum(max(1, round(len(r["summary"].split()) * 1.3)) for r in results)}

    def retrieve_by_id(self, memory_id: str, request: RetrievalRequest) -> dict[str, Any]:
        """Exact lookup still passes the same scope/time/status/revocation policy."""
        rows, excluded = self._eligible(request)
        row = next((candidate for candidate in rows if candidate["memory_id"] == memory_id), None)
        if row is None:
            self._audit("direct_read_denied", request.role, memory_id,
                        details={"decision": "deny", "reason": "not eligible", "excluded": excluded})
            self.conn.commit()
            return {"item": None, "decision": "deny", "reason": "not eligible"}
        item = {"memory_id": row["memory_id"], "memory_type": row["memory_type"],
                "summary": row["summary"], "source_ids": json.loads(row["source_ids"]),
                "evidence_ids": json.loads(row["evidence_ids"]), "status": row["status"],
                "provenance": row["provenance"]}
        self._audit("direct_read_allowed", request.role, memory_id,
                    details={"decision": "allow", "excluded": excluded})
        self.conn.commit()
        return {"item": item, "decision": "allow"}

    def invalidate_source(self, source_id: str, *, actor: str, actor_role: str) -> int:
        if actor_role != "steward":
            raise PermissionError("Source invalidation requires steward authority")
        source = self.conn.execute("SELECT source_id FROM sources WHERE source_id=?", (source_id,)).fetchone()
        if source is None:
            raise ValueError("Unknown source ID")
        affected = []
        for row in self.conn.execute("SELECT memory_id,source_ids FROM episodes WHERE status IN ('approved','pending')"):
            if source_id in json.loads(row["source_ids"]): affected.append(row["memory_id"])
        with self.conn:
            self.conn.execute("UPDATE sources SET status='revoked' WHERE source_id=?", (source_id,))
            for memory_id in affected:
                self.conn.execute("UPDATE episodes SET status='revoked' WHERE memory_id=?", (memory_id,))
                self.conn.execute("DELETE FROM vectors WHERE memory_id=?", (memory_id,))
                self._audit("derived_memory_revoked", actor, memory_id, source_id,
                            details={"serving_blocked": True, "vector_deleted": True})
            self._audit("source_invalidated", actor, source_id=source_id,
                        details={"affected_memory_ids": affected, "raw_source_retained": True})
        return len(affected)

    def forget_expired(self, *, day: int, actor: str = "system") -> int:
        """Remove expired episode vectors from serving while retaining restricted archive rows."""
        rows = self.conn.execute("SELECT memory_id FROM episodes WHERE status='approved' AND memory_type='episodic' AND ? - approved_day > 180", (day,)).fetchall()
        ids = [r[0] for r in rows]
        with self.conn:
            for memory_id in ids:
                self.conn.execute("UPDATE episodes SET status='expired' WHERE memory_id=?", (memory_id,))
                self.conn.execute("DELETE FROM vectors WHERE memory_id=?", (memory_id,))
                self._audit("episode_expired", actor, memory_id, details={"day": day, "archive_retained": True})
        return len(ids)

    def archive_record(self, memory_id: str, *, actor_role: str) -> dict[str, Any] | None:
        if actor_role != "steward":
            raise PermissionError("Restricted archive requires steward authority")
        row = self.conn.execute("SELECT * FROM episodes WHERE memory_id=? AND status IN ('expired','revoked')", (memory_id,)).fetchone()
        return dict(row) if row else None

    def count(self, table: str) -> int:
        if table not in {"episodes", "vectors", "sources", "evidence_records", "audit"}:
            raise ValueError("Unsupported table")
        return int(self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
