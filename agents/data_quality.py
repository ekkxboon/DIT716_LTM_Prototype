"""A1: deterministic signal morphology checks; no cause attribution."""
from __future__ import annotations

from .contracts import Evidence, QualityResult, Scenario


def inspect_signal(scenario: Scenario) -> QualityResult:
    values = [value for value in scenario.values_m if value is not None]
    deltas = [right - left for left, right in zip(values, values[1:])]
    flatline = len(values) >= 3 and len(set(values)) == 1
    rapid_rise = (
        len(values) >= 3
        and all(delta >= 0 for delta in deltas)
        and values[-1] - values[0] >= 0.5
    )
    spike = bool(deltas) and max(abs(delta) for delta in deltas) >= 1.0
    missing = len(values) < len(scenario.values_m)

    tags: list[str] = []
    if flatline:
        tags.append("flatline_morphology")
    if rapid_rise:
        tags.append("rapid_rise_morphology")
    if spike:
        tags.append("spike_morphology")
    if missing:
        tags.append("missingness_morphology")
    if not tags:
        tags.append("no_simple_morphology_flag")

    evidence_id = f"EV-{scenario.case_id}-A1"
    evidence = Evidence(
        evidence_id=evidence_id,
        case_id=scenario.case_id,
        producer="A1",
        kind="measurement_morphology",
        statement=(
            f"A1 observed {len(values)}/{len(scenario.values_m)} numeric readings; "
            f"flatline={flatline}, rapid_rise={rapid_rise}, spike={spike}, missing={missing}."
        ),
        tags=tuple(tags),
        available_day=scenario.decision_day,
    )
    return QualityResult(
        case_id=scenario.case_id,
        valid_count=len(values),
        sample_count=len(scenario.values_m),
        flatline=flatline,
        rapid_rise=rapid_rise,
        spike=spike,
        missing=missing,
        max_step_m=round(max((abs(delta) for delta in deltas), default=0.0), 3),
        evidence=evidence,
    )

