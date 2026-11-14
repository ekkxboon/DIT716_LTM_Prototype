"""Run synthetic cases through the A1 -> A2 -> A3 -> A4 pipeline."""
from __future__ import annotations

import json
from pathlib import Path

from agents.contracts import Evidence, PipelineResult, Scenario
from agents.data_quality import inspect_signal
from agents.diagnostic import draft_diagnosis
from agents.hydrology_context import gather_context
from agents.verifier import verify_draft
from ltm import MemoryGateway


def run_pipeline(
    scenario: Scenario,
    current_evidence: tuple[Evidence, ...],
    memory: MemoryGateway,
    *,
    inject_unsafe_test_claim: bool = False,
) -> PipelineResult:
    quality = inspect_signal(scenario)
    ledger = {quality.evidence.evidence_id: quality.evidence}
    ledger.update({item.evidence_id: item for item in current_evidence})
    context = gather_context(scenario, current_evidence, memory)
    draft = draft_diagnosis(
        scenario,
        quality,
        context,
        inject_unsafe_test_claim=inject_unsafe_test_claim,
    )
    verification = verify_draft(scenario, draft, ledger)
    return PipelineResult(scenario, quality, context, draft, verification)


def load_memory() -> MemoryGateway:
    package_dir = Path(__file__).resolve().parent
    fixture = json.loads((package_dir / "fixtures.json").read_text(encoding="utf-8"))
    memory = MemoryGateway(":memory:")
    memory.seed(fixture)
    return memory


def run_all_cases(memory: MemoryGateway) -> dict[str, PipelineResult]:
    from tools.scenarios import EVIDENCE_BY_CASE, SCENARIOS

    return {
        case_id: run_pipeline(scenario, EVIDENCE_BY_CASE[case_id], memory)
        for case_id, scenario in SCENARIOS.items()
    }


def main() -> None:
    memory = load_memory()
    try:
        for result in run_all_cases(memory).values():
            print(f"{result.scenario.case_id} · A1 spike={result.quality.spike}, "
                  f"flatline={result.quality.flatline}, missing={result.quality.missing}")
            print(f"   A2 current={len(result.context.current_evidence)}, "
                  f"withheld future={len(result.context.withheld_evidence)}, "
                  f"memory analogies={len(result.context.analogies)}")
            print(f"   A3={result.draft.candidate_cause} · abstain={result.draft.abstain}; "
                  f"A4={result.verification.verdict} · human review={result.verification.needs_human_review}")
        print("LTM writes require reviewer approval; run tests for the gated write example.")
    finally:
        memory.close()


if __name__ == "__main__":
    main()
