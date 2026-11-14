"""Controlled four-arm retrieval schedule × episode-age pilot experiment."""
from __future__ import annotations
import csv
import json
import statistics
from pathlib import Path
from ltm import MemoryGateway, RetrievalRequest

ROOT = Path(__file__).parent
CORPUS = json.loads((ROOT / "fixtures.json").read_text())
LABELS = json.loads((ROOT / "evaluation_labels.json").read_text())
CONDITIONS = [
    ("P0", "passive", None),
    ("P1", "active", None),
    ("P2", "passive", 180),
    ("P3", "active", 180),
]


def _violates_policy(db: MemoryGateway, memory_id: str, request: RetrievalRequest) -> bool:
    """Independent fixture-side audit of a returned record against its request."""
    row = db.conn.execute("SELECT * FROM episodes WHERE memory_id=?", (memory_id,)).fetchone()
    if row is None or row["status"] != "approved": return True
    if row["basin"] != request.basin or row["station"] != request.station: return True
    if row["split"] != request.split or row["snapshot_id"] != request.snapshot_id: return True
    if row["memory_type"] not in request.allowed_types: return True
    if request.role not in json.loads(row["allowed_roles"]): return True
    if row["available_day"] > request.query_day or row["approved_day"] > request.query_day: return True
    if not row["valid_from_day"] <= request.observation_day <= row["valid_to_day"]: return True
    if row["review_due_day"] is not None and row["review_due_day"] < request.query_day: return True
    if request.max_age_days is not None and request.query_day - row["approved_day"] > request.max_age_days: return True
    for source_id in json.loads(row["source_ids"]):
        source = db.conn.execute("SELECT status FROM sources WHERE source_id=?", (source_id,)).fetchone()
        if source is None or source[0] != "active": return True
    return False


def run_experiment(output_csv: Path | None = None,
                  case_output_csv: Path | None = None) -> list[dict]:
    rows, case_rows, db = [], [], MemoryGateway(":memory:")
    db.seed(CORPUS)
    for condition, schedule, ttl in CONDITIONS:
        retrieved_relevant = retrieved_total = gold_total = calls = estimated_tokens = forbidden = 0
        ttl_excluded = unavailable_excluded = revoked_excluded = 0
        latencies = []
        for query in LABELS["query_cases"]:
            returned: dict[str, dict] = {}
            texts = [query["text"]]
            if schedule == "active":
                texts += query["followups"][:2]
            gold = set(query["relevant_ids"])
            gold_total += len(gold)
            for text in texts:
                request = RetrievalRequest(text=text, query_day=CORPUS["decision_day"],
                                           observation_day=CORPUS["decision_day"], max_age_days=ttl, top_k=1)
                result = db.retrieve(request)
                calls += 1; latencies.append(result["latency_ms"]); estimated_tokens += result["context_tokens_estimate"]
                ttl_excluded += result["excluded"]["expired_ttl"]
                unavailable_excluded += result["excluded"]["not_yet_available"]
                revoked_excluded += result["excluded"]["revoked_source"]
                for item in result["items"]:
                    returned[item["memory_id"]] = item
                    if _violates_policy(db, item["memory_id"], request): forbidden += 1
            found = set(returned)
            retrieved_total += len(found)
            hits = found & gold
            retrieved_relevant += len(hits)
            case_rows.append({"condition": condition, "query_id": query["query_id"],
                              "gold_ids": "|".join(sorted(gold)), "retrieved_ids": "|".join(sorted(found)),
                              "relevant_hits": len(hits), "gold_count": len(gold),
                              "case_precision": round(len(hits)/len(found), 4) if found else 0.0,
                              "case_recall": round(len(hits)/len(gold), 4) if gold else 0.0})
            # This corpus is fixture-labeled; any returned non-gold item is a false positive.
        precision = retrieved_relevant / retrieved_total if retrieved_total else 0.0
        recall = retrieved_relevant / gold_total if gold_total else 0.0
        rows.append({"condition": condition, "schedule": schedule, "episode_ttl_days": "none" if ttl is None else ttl,
                     "queries": len(LABELS["query_cases"]), "gold_relevant": gold_total,
                     "retrieved_unique": retrieved_total, "relevant_retrieved": retrieved_relevant,
                     "precision": round(precision, 4), "recall": round(recall, 4),
                     "retrieval_calls": calls, "avg_calls_per_query": round(calls/len(LABELS["query_cases"]), 2),
                     "estimated_context_tokens": estimated_tokens, "p50_retrieval_ms": round(statistics.median(latencies), 4),
                     "forbidden_retrievals": forbidden, "ttl_excluded_candidate_checks": ttl_excluded,
                     "unavailable_at_decision_exclusions": unavailable_excluded,
                     "revoked_source_exclusions": revoked_excluded,
                     "expired_episode_ttl_days": ttl if ttl is not None else "disabled"})
    db.close()
    if output_csv:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        with output_csv.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    if case_output_csv:
        case_output_csv.parent.mkdir(parents=True, exist_ok=True)
        with case_output_csv.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(case_rows[0])); writer.writeheader(); writer.writerows(case_rows)
    return rows


if __name__ == "__main__":
    out = ROOT / "results" / "policy_results.csv"
    case_out = ROOT / "results" / "policy_case_results.csv"
    print(json.dumps(run_experiment(out, case_out), indent=2))
    print(f"\nWrote {out.relative_to(ROOT)} and {case_out.relative_to(ROOT)}")
