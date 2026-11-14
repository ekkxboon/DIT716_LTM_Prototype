"""A3 may propose a source-linked LTM summary after A4 verification; never approve it."""
from __future__ import annotations

from ltm import MemoryGateway

from .contracts import PipelineResult


def propose_verified_episode(memory: MemoryGateway, result: PipelineResult) -> str:
    """Create a pending summary only for a traceable, non-abstained hypothesis."""
    check = result.verification
    if check.verdict != "traceable hypothesis" or check.needs_human_review or not check.cited_ids_valid:
        raise PermissionError("Only A4-traceable, non-abstained hypotheses may be proposed to LTM")
    if result.draft.candidate_cause == "unknown / insufficient evidence":
        raise ValueError("Unknown outcomes are not promoted as candidate episodes")

    case_id = result.scenario.case_id
    source_id = f"SRC-AGENT-DEMO-{case_id}"
    memory_id = f"EP-AGENT-DEMO-{case_id}"
    with memory.conn:
        memory.conn.execute(
            "INSERT OR IGNORE INTO sources(source_id,kind,status) VALUES(?,?,?)",
            (source_id, "synthetic_agent_demo", "active"),
        )
        for evidence_id in result.draft.evidence_ids:
            memory.conn.execute(
                "INSERT OR IGNORE INTO evidence_records(evidence_id,source_id) VALUES(?,?)",
                (evidence_id, source_id),
            )
    snapshot_id = memory.conn.execute("SELECT snapshot_id FROM episodes LIMIT 1").fetchone()[0]
    memory.propose_summary(
        memory_id=memory_id,
        station=result.scenario.station,
        basin=result.scenario.basin,
        observed_morphology=(
            f"flatline={result.quality.flatline}, rapid_rise={result.quality.rapid_rise}, "
            f"spike={result.quality.spike}, missing={result.quality.missing}"
        ),
        candidate_hypothesis=f"{result.draft.candidate_cause} is a candidate, not an adjudicated outcome",
        source_ids=[source_id],
        evidence_ids=result.draft.evidence_ids,
        producer_role="A3",
        split="train",
        snapshot_id=snapshot_id,
        day=result.scenario.decision_day,
    )
    return memory_id


def approve_proposed_episode(
    memory: MemoryGateway,
    memory_id: str,
    *,
    reviewer_id: str,
    reviewer_role: str,
    day: int,
) -> None:
    """Delegate approval to the LTM gateway's reviewer authorization."""
    memory.approve_episode(
        memory_id,
        reviewer_id=reviewer_id,
        reviewer_role=reviewer_role,
        day=day,
    )

