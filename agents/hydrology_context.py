"""A2: current context and policy-filtered memory analogies."""
from __future__ import annotations

from ltm import MemoryGateway, RetrievalRequest

from .contracts import ContextResult, Evidence, Scenario

_MEMORY_QUERIES = {
    "C1": "rapid stage rise after upstream rainfall neighboring gauge lag",
    "C2": "stage gauge flatline frozen sensor repeated value",
    "C3": "abrupt stage spike no corroborating hydrology context",
    "C4": "maintenance modem reset delayed packet timestamp shift",
}


def gather_context(
    scenario: Scenario,
    current_records: tuple[Evidence, ...],
    memory: MemoryGateway,
) -> ContextResult:
    """Retrieve scoped memories, keeping them separate from current evidence."""
    available = tuple(row for row in current_records if row.available_day <= scenario.decision_day)
    withheld = tuple(row for row in current_records if row.available_day > scenario.decision_day)
    request = RetrievalRequest(
        text=f"{scenario.station} {_MEMORY_QUERIES.get(scenario.case_id, 'hydrology stage context')}",
        role="A2",
        basin=scenario.basin,
        station=scenario.station,
        query_day=scenario.decision_day,
        observation_day=scenario.decision_day,
        top_k=2,
        max_age_days=180,
    )
    retrieved = memory.retrieve(request)
    analogies = tuple(
        {
            "memory_id": item["memory_id"],
            "summary": item["summary"],
            "status": item["status"],
        }
        for item in retrieved["items"]
    )
    return ContextResult(
        case_id=scenario.case_id,
        current_evidence=available,
        withheld_evidence=withheld,
        analogies=analogies,
        excluded_memory_counts=dict(retrieved["excluded"]),
    )
