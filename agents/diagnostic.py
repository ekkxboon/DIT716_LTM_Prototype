"""A3: differential diagnosis; conclusions remain hypotheses by default."""
from __future__ import annotations

from .contracts import ContextResult, DiagnosticDraft, QualityResult, Scenario


def draft_diagnosis(
    scenario: Scenario,
    quality: QualityResult,
    context: ContextResult,
    *,
    inject_unsafe_test_claim: bool = False,
) -> DiagnosticDraft:
    """Create a candidate diagnosis. The unsafe branch is only for verifier tests."""
    evidence_ids = (quality.evidence.evidence_id,) + tuple(
        evidence.evidence_id for evidence in context.current_evidence
    )
    if quality.spike and inject_unsafe_test_claim:
        return DiagnosticDraft(
            case_id=scenario.case_id,
            candidate_cause="suspicious manipulation",
            claim="Malicious manipulation confirmed from the spike morphology.",
            claim_kind="adjudicated_outcome",
            evidence_ids=evidence_ids,
            alternatives=(),
            abstain=False,
        )

    tags = {tag for item in context.current_evidence for tag in item.tags}
    if quality.rapid_rise and "supports_genuine_event" in tags:
        cause = "genuine hydrological event"
        claim = "A rising stage is a candidate event; rainfall and upstream-gauge context are consistent."
        alternatives = ("sensor/data-quality fault", "telemetry/configuration fault")
        abstain = False
    elif quality.flatline:
        cause = "sensor/data-quality fault"
        claim = "A flatline makes a sensor/data-quality fault a candidate; morphology alone does not confirm it."
        alternatives = ("stable local condition", "telemetry/replay issue")
        abstain = False
    elif quality.missing and "packet_delay_observed" in tags:
        cause = "unknown / insufficient evidence"
        claim = "Packet delay is observed, but available evidence cannot distinguish telemetry from sensor causes."
        alternatives = ("telemetry/configuration fault", "sensor/data-quality fault")
        abstain = True
    elif quality.spike:
        cause = "unknown / insufficient evidence"
        claim = "An abrupt spike is observed, but the available evidence does not identify its cause."
        alternatives = (
            "genuine hydrological event",
            "sensor/data-quality fault",
            "telemetry/configuration fault",
        )
        abstain = True
    else:
        cause = "unknown / insufficient evidence"
        claim = "The available evidence does not support a cause-level conclusion."
        alternatives = ("genuine event", "sensor/data-quality fault")
        abstain = True

    return DiagnosticDraft(
        case_id=scenario.case_id,
        candidate_cause=cause,
        claim=claim,
        claim_kind="hypothesis",
        evidence_ids=evidence_ids,
        alternatives=alternatives,
        abstain=abstain,
    )
