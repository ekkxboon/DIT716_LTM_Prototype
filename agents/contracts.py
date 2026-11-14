"""Typed input/output contracts shared by the agent pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Scenario:
    case_id: str
    station: str
    basin: str
    decision_day: int
    values_m: tuple[float | None, ...]


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    case_id: str
    producer: Literal["A1", "A2"]
    kind: str
    statement: str
    tags: tuple[str, ...]
    available_day: int


@dataclass(frozen=True)
class QualityResult:
    case_id: str
    valid_count: int
    sample_count: int
    flatline: bool
    rapid_rise: bool
    spike: bool
    missing: bool
    max_step_m: float
    evidence: Evidence


@dataclass(frozen=True)
class ContextResult:
    case_id: str
    current_evidence: tuple[Evidence, ...]
    withheld_evidence: tuple[Evidence, ...]
    analogies: tuple[dict[str, str], ...]
    excluded_memory_counts: dict[str, int]


@dataclass(frozen=True)
class DiagnosticDraft:
    case_id: str
    candidate_cause: str
    claim: str
    claim_kind: Literal["hypothesis", "adjudicated_outcome"]
    evidence_ids: tuple[str, ...]
    alternatives: tuple[str, ...]
    abstain: bool


@dataclass(frozen=True)
class VerificationResult:
    case_id: str
    verdict: Literal["traceable hypothesis", "downgraded / escalate", "escalate"]
    candidate_after_verification: str
    abstain: bool
    needs_human_review: bool
    violations: tuple[str, ...]
    cited_ids_valid: bool
    verified_true_cause: Literal[False] = False


@dataclass(frozen=True)
class PipelineResult:
    scenario: Scenario
    quality: QualityResult
    context: ContextResult
    draft: DiagnosticDraft
    verification: VerificationResult
