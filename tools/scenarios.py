"""Synthetic scenario fixtures; not real station observations."""
from agents.contracts import Evidence, Scenario

C3_SPIKE = Scenario(
    case_id="C3",
    station="S17",
    basin="BASIN-1",
    decision_day=365,
    values_m=(1.08, 1.10, 3.35, 1.12),
)

C1_RISE = Scenario("C1", "S17", "BASIN-1", 365, (1.20, 1.27, 1.51, 1.91))
C2_FLATLINE = Scenario("C2", "S17", "BASIN-1", 365, (1.46, 1.46, 1.46, 1.46))
C4_DELAYED = Scenario("C4", "S17", "BASIN-1", 365, (0.82, None, 0.84, None))

SCENARIOS = {case.case_id: case for case in (C1_RISE, C2_FLATLINE, C3_SPIKE, C4_DELAYED)}

C1_EVIDENCE = (
    Evidence("EV-C1-RAIN", "C1", "A2", "rainfall", "Rainfall increased upstream during the event window.",
             ("rainfall_observed",), 365),
    Evidence("EV-C1-UP", "C1", "A2", "neighbor_gauge", "An upstream gauge also rose within the plausible lag window.",
             ("upstream_rise", "supports_genuine_event"), 365),
)
C2_EVIDENCE = (
    Evidence("EV-C2-RAIN", "C2", "A2", "rainfall", "No notable rainfall was recorded in this short window.",
             ("no_rainfall_corroboration",), 365),
    Evidence("EV-C2-NEIGHBOR", "C2", "A2", "neighbor_gauge", "The neighboring gauge changed gradually rather than remaining flat.",
             ("neighbor_not_flat",), 365),
)
# C3 intentionally has no current rainfall, neighbor-gauge, or provenance records.
C3_CURRENT_EVIDENCE: tuple[Evidence, ...] = ()
C4_EVIDENCE = (
    Evidence("EV-C4-PACKET", "C4", "A2", "telemetry", "Receive timestamps show a delayed packet burst.",
             ("packet_delay_observed",), 365),
    # This record exists, but the context agent must withhold it at day 365.
    Evidence("EV-C4-MAINT", "C4", "A2", "maintenance", "A maintenance note records a modem reset.",
             ("maintenance_reset",), 366),
)

EVIDENCE_BY_CASE = {
    "C1": C1_EVIDENCE,
    "C2": C2_EVIDENCE,
    "C3": C3_CURRENT_EVIDENCE,
    "C4": C4_EVIDENCE,
}
