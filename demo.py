"""Run the guided CLI demonstration: python3 demo.py"""
from __future__ import annotations
import json
import tempfile
from pathlib import Path
from ltm import MemoryGateway, RetrievalRequest
from experiment import CORPUS, run_experiment


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="dit716_ltm_") as tmp:
        db = MemoryGateway(Path(tmp) / "demo.sqlite")
        db.seed(CORPUS)
        print("DIT 716 · Simplified governed LTM demo")
        print("Synthetic offline fixtures only; no field data or LLM is used.\n")
        print("1) Passive semantic retrieval for an S17 flatline:")
        result = db.retrieve(RetrievalRequest("S17 stage gauge flatline frozen sensor stuck value"))
        for item in result["items"]:
            print(f"   {item['memory_id']}  cosine={item['similarity']:.3f}  {item['summary']}")
        print(f"   excluded by policy: {result['excluded']}\n")
        print("2) Propose → approve → retrieve a source-linked episode:")
        summary = db.propose_summary(memory_id="EP-DEMO", station="S17", basin="BASIN-1",
            observed_morphology="delayed packet arrival", candidate_hypothesis="telemetry interruption",
            source_ids=["SRC-103"], evidence_ids=["EV-103"])
        print("   proposal:", summary)
        print("   pending vector count:", db.count("vectors"))
        try:
            db.approve_episode("EP-DEMO", reviewer_id="agent-A3", reviewer_role="agent")
        except PermissionError as exc:
            print("   agent approval denied:", exc)
        db.approve_episode("EP-DEMO", reviewer_id="reviewer-demo", reviewer_role="reviewer")
        print("   approved vector count:", db.count("vectors"))
        print("   source-linked retrieval:", [x["memory_id"] for x in db.retrieve(
            RetrievalRequest("S17 stage dropout telemetry interruption"))["items"]], "\n")
        print("3) Forgetting checks:")
        before = db.count("vectors")
        expired = db.forget_expired(day=CORPUS["decision_day"])
        print(f"   TTL cleanup removed {expired} expired vector(s); vectors {before}→{db.count('vectors')}")
        try:
            db.archive_record("EP-005", actor_role="A3")
        except PermissionError as exc:
            print("   expired archive denied to agent:", exc)
        archive = db.archive_record("EP-005", actor_role="steward")
        print("   steward can inspect restricted archive:", bool(archive))
        affected = db.invalidate_source("SRC-115", actor="steward-demo", actor_role="steward")
        print(f"   revoking SRC-115 blocked {affected} dependent record(s); vectors now {db.count('vectors')}")
        print("   retrieval after revocation:", db.retrieve(RetrievalRequest("S17 later maintenance sensor reset"))["items"])
        db.close()
    print("\n4) Four-condition experiment (same query cases and frozen corpus):")
    for row in run_experiment():
        print(f"   {row['condition']}: precision={row['precision']:.3f}, recall={row['recall']:.3f}, "
              f"calls/query={row['avg_calls_per_query']:.2f}, forbidden={row['forbidden_retrievals']}")
    results_path = Path(__file__).parent / "results" / "policy_results.csv"
    case_results_path = Path(__file__).parent / "results" / "policy_case_results.csv"
    run_experiment(results_path, case_results_path)
    print(f"   CSVs: {results_path.relative_to(Path(__file__).parent)}, "
          f"{case_results_path.relative_to(Path(__file__).parent)}")

if __name__ == "__main__":
    main()
