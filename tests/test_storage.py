import tempfile
import unittest
from pathlib import Path

from agent.storage import RunStore


class RunStoreTests(unittest.TestCase):
    def test_json_and_event_artifacts_are_scoped_to_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = RunStore(directory, "test-run")
            store.write_json("run_manifest.json", {"records": 100})
            store.append_event("seed", "ok", count=100)
            self.assertEqual(store.read_json("run_manifest.json")["records"], 100)
            self.assertIn('"stage": "seed"', (Path(directory) / "test-run/logs/event_log.jsonl").read_text(encoding="utf-8"))

    def test_store_rejects_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = RunStore(directory, "test-run")
            with self.assertRaises(ValueError):
                store.write_json("../outside.json", {})


if __name__ == "__main__":
    unittest.main()
