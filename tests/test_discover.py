import importlib.util
import unittest
from datetime import datetime, timezone
from pathlib import Path

spec = importlib.util.spec_from_file_location("discover", Path(__file__).resolve().parents[1] / "scripts/discover.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 22, tzinfo=timezone.utc)

    def test_classifies_and_deduplicates(self):
        hit = {"title": "MLIR tensor compiler optimization", "url": "https://example.org/paper", "points": 12, "num_comments": 5, "created_at_i": int(self.now.timestamp())}
        added = module.discover([], self.now, lambda q, since: [hit])
        self.assertEqual(len(added), 1)
        self.assertIn("array-compilers", added[0]["projects"])
        self.assertEqual(module.discover(added, self.now, lambda q, since: [hit]), [])

    def test_ignores_unrelated_and_low_quality(self):
        hits = [
            {"title": "Unrelated story", "url": "https://example.org/1", "points": 100, "created_at_i": int(self.now.timestamp())},
            {"title": "MLIR compiler", "url": "https://example.org/2", "points": 1, "num_comments": 0, "created_at_i": int(self.now.timestamp())},
        ]
        self.assertEqual(module.discover([], self.now, lambda q, since: hits), [])

    def test_preserves_data_when_sources_fail(self):
        def fail(q, since):
            raise RuntimeError("network down")
        with self.assertRaises(RuntimeError):
            module.discover([], self.now, fail)

if __name__ == "__main__":
    unittest.main()
