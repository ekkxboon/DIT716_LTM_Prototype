from __future__ import annotations
import json
import unittest
from pathlib import Path
from ltm import MemoryGateway, RetrievalRequest

FIXTURE = json.loads((Path(__file__).parent / "fixtures.json").read_text())


class LTMPolicyTests(unittest.TestCase):
    def setUp(self):
        self.db = MemoryGateway(":memory:")
        self.db.seed(FIXTURE)

    def tearDown(self): self.db.close()

    def test_scope_split_status_availability_and_role_are_enforced(self):
        base = self.db.retrieve(RetrievalRequest("S17 flatline frozen stage sensor"))
        ids = {x["memory_id"] for x in base["items"]}
        self.assertNotIn("EP-011", ids)  # other basin/station
        self.assertNotIn("EP-014", ids)  # pending, no vector
        self.assertNotIn("EP-004", ids)  # not yet available at decision time
        self.assertGreaterEqual(base["excluded"]["not_yet_available"], 1)
        wrong_role = self.db.retrieve(RetrievalRequest("concise English profile", role="A4", allowed_types=("profile",)))
        self.assertEqual(wrong_role["items"], [])
        self.assertEqual(wrong_role["excluded"]["type_not_implemented"], 1)
        self.assertNotIn("query_cases", FIXTURE)  # evaluator labels stay outside the memory corpus
        self.assertTrue(all(row.get("split", "train") == "train" for row in FIXTURE["episodes"]))

    def test_exact_id_reads_share_policy_and_profile_is_not_embedded(self):
        request = RetrievalRequest("flatline")
        self.assertEqual(self.db.retrieve_by_id("EP-001", request)["decision"], "allow")
        self.assertEqual(self.db.retrieve_by_id("EP-014", request)["decision"], "deny")  # pending
        self.assertEqual(self.db.retrieve_by_id("EP-011", request)["decision"], "deny")  # other basin
        self.assertEqual(self.db.retrieve_by_id("EP-004", request)["decision"], "deny")  # delayed availability
        self.assertIsNone(self.db.conn.execute("SELECT 1 FROM vectors WHERE memory_id='EP-013'").fetchone())
        profile_request = RetrievalRequest("profile", role="A3", allowed_types=("profile",))
        self.assertEqual(self.db.retrieve_by_id("EP-013", profile_request)["decision"], "deny")

    def test_ttl_expires_serving_index_but_keeps_restricted_archive(self):
        with_ttl = self.db.retrieve(RetrievalRequest("S17 old frozen sensor reboot", max_age_days=180))
        no_ttl = self.db.retrieve(RetrievalRequest("S17 old frozen sensor reboot", max_age_days=None))
        self.assertNotIn("EP-005", {x["memory_id"] for x in with_ttl["items"]})
        self.assertIn("EP-005", {x["memory_id"] for x in no_ttl["items"]})
        self.assertGreater(with_ttl["excluded"]["expired_ttl"], 0)
        removed = self.db.forget_expired(day=FIXTURE["decision_day"])
        self.assertGreaterEqual(removed, 1)
        self.assertEqual(self.db.archive_record("EP-005", actor_role="steward")["status"], "expired")
        with self.assertRaises(PermissionError): self.db.archive_record("EP-005", actor_role="A3")
        self.assertNotIn("EP-005", {x["memory_id"] for x in self.db.retrieve(
            RetrievalRequest("S17 old frozen sensor reboot", max_age_days=None))["items"]})

    def test_proposal_needs_human_approval_before_vectorization(self):
        summary = self.db.propose_summary(memory_id="EP-TEST", station="S17", basin="BASIN-1",
            observed_morphology="flat stage", candidate_hypothesis="sensor freeze",
            source_ids=["SRC-101"], evidence_ids=["EV-101"])
        self.assertIn("not an adjudicated outcome", summary)
        with self.assertRaises(ValueError):
            self.db.propose_summary(memory_id="EP-UNKNOWN", station="S17", basin="BASIN-1",
                observed_morphology="flat stage", candidate_hypothesis="unsupported cause",
                source_ids=["SRC-101"], evidence_ids=["EV-NOT-IN-LEDGER"])
        self.assertEqual(self.db.conn.execute("SELECT status FROM episodes WHERE memory_id='EP-TEST'").fetchone()[0], "pending")
        self.assertIsNone(self.db.conn.execute("SELECT 1 FROM vectors WHERE memory_id='EP-TEST'").fetchone())
        with self.assertRaises(PermissionError):
            self.db.approve_episode("EP-TEST", reviewer_id="A3", reviewer_role="A3")
        self.db.approve_episode("EP-TEST", reviewer_id="reviewer", reviewer_role="reviewer")
        self.assertIsNotNone(self.db.conn.execute("SELECT 1 FROM vectors WHERE memory_id='EP-TEST'").fetchone())

    def test_revocation_cascades_to_summary_and_vector_index(self):
        before = self.db.count("vectors")
        affected = self.db.invalidate_source("SRC-115", actor="steward", actor_role="steward")
        self.assertEqual(affected, 1)
        self.assertEqual(self.db.count("vectors"), before - 1)
        result = self.db.retrieve(RetrievalRequest("S17 later maintenance sensor reset"))
        self.assertNotIn("EP-015", {x["memory_id"] for x in result["items"]})
        self.assertEqual(self.db.archive_record("EP-015", actor_role="steward")["status"], "revoked")
        with self.assertRaises(PermissionError): self.db.invalidate_source("SRC-101", actor="A3", actor_role="A3")

    @unittest.skipUnless((Path(__file__).parent / "evaluation_labels.json").exists(),
                         "requires local evaluator-only labels; kept out of the public repository")
    def test_four_arm_policy_experiment_is_reproducible_and_zero_forbidden(self):
        from experiment import run_experiment
        import csv, tempfile
        from pathlib import Path
        first, second = run_experiment(), run_experiment()
        self.assertEqual([x["condition"] for x in first], ["P0", "P1", "P2", "P3"])
        keys = ("precision", "recall", "retrieval_calls", "ttl_excluded_candidate_checks",
                "unavailable_at_decision_exclusions", "forbidden_retrievals")
        self.assertEqual([tuple(x[k] for k in keys) for x in first],
                         [tuple(x[k] for k in keys) for x in second])
        self.assertTrue(all(x["forbidden_retrievals"] == 0 for x in first))
        self.assertTrue(all(x["recall"] <= 1.0 and x["precision"] <= 1.0 for x in first))
        with tempfile.TemporaryDirectory() as tmp:
            case_file = Path(tmp) / "case.csv"
            run_experiment(case_output_csv=case_file)
            with case_file.open() as stream:
                cases = list(csv.DictReader(stream))
        p0_q4 = next(r for r in cases if r["condition"] == "P0" and r["query_id"] == "Q4")
        p2_q4 = next(r for r in cases if r["condition"] == "P2" and r["query_id"] == "Q4")
        p0_q2 = next(r for r in cases if r["condition"] == "P0" and r["query_id"] == "Q2")
        p2_q2 = next(r for r in cases if r["condition"] == "P2" and r["query_id"] == "Q2")
        self.assertIn("EP-005", p0_q4["retrieved_ids"])
        self.assertNotIn("EP-005", p2_q4["retrieved_ids"])
        self.assertNotIn("EP-008", p0_q2["retrieved_ids"])
        self.assertIn("EP-008", p2_q2["retrieved_ids"])


if __name__ == "__main__": unittest.main(verbosity=2)
