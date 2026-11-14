from __future__ import annotations

import unittest

from agents.contracts import DiagnosticDraft, Evidence
from agents.data_quality import inspect_signal
from agents.memory_writer import approve_proposed_episode, propose_verified_episode
from agents.verifier import verify_draft
from ltm import RetrievalRequest
from orchestrator import load_memory, run_all_cases, run_pipeline
from tools.scenarios import C3_CURRENT_EVIDENCE, C3_SPIKE


class AgentPipelineTests(unittest.TestCase):
    def setUp(self):
        self.memory = load_memory()

    def tearDown(self):
        self.memory.close()

    def test_c3_end_to_end_abstains_without_current_corroboration(self):
        result = run_pipeline(C3_SPIKE, C3_CURRENT_EVIDENCE, self.memory)
        self.assertTrue(result.quality.spike)
        self.assertEqual(result.quality.max_step_m, 2.25)
        self.assertEqual(result.context.current_evidence, ())
        self.assertTrue(result.context.analogies)  # memory is context, not current evidence
        self.assertEqual(result.draft.candidate_cause, "unknown / insufficient evidence")
        self.assertTrue(result.draft.abstain)
        self.assertEqual(result.verification.verdict, "escalate")
        self.assertTrue(result.verification.needs_human_review)
        self.assertFalse(result.verification.verified_true_cause)

    def test_all_four_cases_have_expected_candidates_and_time_filtering(self):
        results = run_all_cases(self.memory)
        self.assertEqual(set(results), {"C1", "C2", "C3", "C4"})
        self.assertEqual(results["C1"].draft.candidate_cause, "genuine hydrological event")
        self.assertEqual(results["C2"].draft.candidate_cause, "sensor/data-quality fault")
        self.assertEqual(results["C3"].draft.candidate_cause, "unknown / insufficient evidence")
        self.assertEqual(results["C4"].draft.candidate_cause, "unknown / insufficient evidence")
        self.assertEqual(results["C1"].verification.verdict, "traceable hypothesis")
        self.assertEqual(results["C2"].verification.verdict, "traceable hypothesis")
        self.assertTrue(results["C3"].verification.needs_human_review)
        self.assertTrue(results["C4"].verification.needs_human_review)
        self.assertEqual([row.evidence_id for row in results["C4"].context.current_evidence], ["EV-C4-PACKET"])
        self.assertEqual([row.evidence_id for row in results["C4"].context.withheld_evidence], ["EV-C4-MAINT"])

    def test_only_verified_candidate_can_be_proposed_and_reviewer_approves(self):
        results = run_all_cases(self.memory)
        with self.assertRaises(PermissionError):
            propose_verified_episode(self.memory, results["C3"])

        memory_id = propose_verified_episode(self.memory, results["C1"])
        status = self.memory.conn.execute(
            "SELECT status FROM episodes WHERE memory_id=?", (memory_id,)
        ).fetchone()[0]
        self.assertEqual(status, "pending")
        self.assertIsNone(self.memory.conn.execute(
            "SELECT 1 FROM vectors WHERE memory_id=?", (memory_id,)
        ).fetchone())
        request = RetrievalRequest("rapid stage rise", role="A3", station="S17", basin="BASIN-1",
                                   query_day=365, observation_day=365, snapshot_id="dit716-ltm-pilot-v1")
        self.assertEqual(self.memory.retrieve_by_id(memory_id, request)["decision"], "deny")

        with self.assertRaises(PermissionError):
            approve_proposed_episode(self.memory, memory_id, reviewer_id="A3", reviewer_role="A3", day=365)
        approve_proposed_episode(self.memory, memory_id, reviewer_id="reviewer-1",
                                 reviewer_role="reviewer", day=365)
        self.assertEqual(self.memory.retrieve_by_id(memory_id, request)["decision"], "allow")

    def test_a4_downgrades_injected_malicious_claim(self):
        result = run_pipeline(
            C3_SPIKE,
            C3_CURRENT_EVIDENCE,
            self.memory,
            inject_unsafe_test_claim=True,
        )
        self.assertEqual(result.draft.candidate_cause, "suspicious manipulation")
        self.assertEqual(result.verification.candidate_after_verification, "unknown / insufficient evidence")
        self.assertIn("signal morphology cannot establish malicious intent", result.verification.violations)
        self.assertIn("agent cannot publish an adjudicated outcome", result.verification.violations)
        self.assertTrue(result.verification.needs_human_review)

    def test_a4_rejects_cross_case_and_future_evidence(self):
        quality = inspect_signal(C3_SPIKE)
        foreign = Evidence("EV-OTHER", "C2", "A2", "neighbor_gauge", "neighbor rose", (), 365)
        future = Evidence("EV-FUTURE", "C3", "A2", "maintenance", "note", (), 366)
        draft = DiagnosticDraft(
            case_id="C3",
            candidate_cause="unknown / insufficient evidence",
            claim="Not enough evidence.",
            claim_kind="hypothesis",
            evidence_ids=(quality.evidence.evidence_id, foreign.evidence_id, future.evidence_id),
            alternatives=(),
            abstain=True,
        )
        checked = verify_draft(C3_SPIKE, draft, {
            quality.evidence.evidence_id: quality.evidence,
            foreign.evidence_id: foreign,
            future.evidence_id: future,
        })
        self.assertIn("evidence belongs to another case", checked.violations)
        self.assertIn("evidence unavailable at decision time", checked.violations)
        self.assertFalse(checked.cited_ids_valid)
        self.assertTrue(checked.needs_human_review)


if __name__ == "__main__":
    unittest.main(verbosity=2)
