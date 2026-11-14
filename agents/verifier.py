"""A4: validate evidence lineage and enforce conservative claim policies."""
from __future__ import annotations

from collections.abc import Mapping

from .contracts import DiagnosticDraft, Evidence, Scenario, VerificationResult


def verify_draft(
    scenario: Scenario,
    draft: DiagnosticDraft,
    evidence_ledger: Mapping[str, Evidence],
) -> VerificationResult:
    violations: list[str] = []
    references = draft.evidence_ids
    missing = [evidence_id for evidence_id in references if evidence_id not in evidence_ledger]
    wrong_case = [
        evidence_id
        for evidence_id in references
        if evidence_id in evidence_ledger
        and evidence_ledger[evidence_id].case_id != scenario.case_id
    ]
    future = [
        evidence_id
        for evidence_id in references
        if evidence_id in evidence_ledger
        and evidence_ledger[evidence_id].available_day > scenario.decision_day
    ]
    tags = {
        tag
        for evidence_id in references
        if evidence_id in evidence_ledger
        for tag in evidence_ledger[evidence_id].tags
    }

    if missing:
        violations.append("evidence ID not found")
    if wrong_case:
        violations.append("evidence belongs to another case")
    if future:
        violations.append("evidence unavailable at decision time")
    if draft.candidate_cause == "suspicious manipulation" and "independent_malicious_provenance" not in tags:
        violations.append("signal morphology cannot establish malicious intent")
    if draft.claim_kind == "adjudicated_outcome":
        violations.append("agent cannot publish an adjudicated outcome")

    blocked = bool(violations)
    abstain = draft.abstain or blocked
    candidate = "unknown / insufficient evidence" if blocked else draft.candidate_cause
    verdict = (
        "downgraded / escalate"
        if blocked
        else "escalate"
        if abstain
        else "traceable hypothesis"
    )
    return VerificationResult(
        case_id=scenario.case_id,
        verdict=verdict,
        candidate_after_verification=candidate,
        abstain=abstain,
        needs_human_review=abstain or blocked,
        violations=tuple(violations),
        cited_ids_valid=not (missing or wrong_case or future),
    )

