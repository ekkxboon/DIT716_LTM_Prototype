from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.build_pages import build_site


class GitHubPagesBuildTests(unittest.TestCase):
    def test_static_bundle_has_demo_data_but_excludes_evaluator_labels(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = build_site(Path(temporary) / "pages")
            self.assertTrue((destination / "index.html").is_file())
            self.assertTrue((destination / "app.js").is_file())
            self.assertTrue((destination / "data" / "fixtures.json").is_file())
            self.assertTrue((destination / "data" / "policy_results.csv").is_file())
            self.assertFalse(any(destination.rglob("evaluation_labels.json")))
            self.assertFalse(any(destination.rglob("policy_case_results.csv")))
            self.assertFalse(any(destination.rglob("*.py")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
