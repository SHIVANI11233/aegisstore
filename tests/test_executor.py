import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from aegisstore import executor


class ExecutorBatchTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file = Path(self.temp_dir.name) / "test.txt"
        self.test_file.write_text("test data")

    def tearDown(self):
        self.temp_dir.cleanup()
        if executor.QUARANTINE_DIR.exists():
            import shutil
            shutil.rmtree(executor.QUARANTINE_DIR)

    def test_batch_quarantine_single_candidate(self):
        candidates = [{"path": str(self.test_file), "reason": "test cleanup"}]
        load = {"state": "NORMAL", "cpu_percent": 50}
        
        result = executor.batch_quarantine(candidates, load, verify_safety=False)
        
        self.assertEqual(len(result["executed"]), 1)
        self.assertEqual(len(result["failed"]), 0)
        self.assertEqual(len(result["skipped"]), 0)
        self.assertGreater(result["total_bytes_recovered"], 0)
        self.assertFalse(self.test_file.exists())

    def test_batch_quarantine_system_busy_defers(self):
        candidates = [{"path": str(self.test_file), "reason": "test cleanup"}]
        load = {"state": "CRITICAL", "cpu_percent": 92}
        
        result = executor.batch_quarantine(candidates, load, verify_safety=True)
        
        self.assertEqual(len(result["executed"]), 0)
        self.assertEqual(len(result["skipped"]), len(candidates))
        self.assertFalse(result["safety_cleared"])
        self.assertTrue(self.test_file.exists())

    def test_batch_quarantine_missing_file_fails(self):
        candidates = [{"path": "/nonexistent/file.txt", "reason": "test"}]
        load = {"state": "NORMAL"}
        
        result = executor.batch_quarantine(candidates, load, verify_safety=False)
        
        self.assertEqual(len(result["executed"]), 0)
        self.assertEqual(len(result["failed"]), 1)
        self.assertIn("does not exist", result["failed"][0]["error"])

    def test_batch_quarantine_multiple_candidates(self):
        file1 = Path(self.temp_dir.name) / "file1.txt"
        file2 = Path(self.temp_dir.name) / "file2.txt"
        file1.write_text("data1")
        file2.write_text("data2")
        
        candidates = [
            {"path": str(file1), "reason": "cleanup 1"},
            {"path": str(file2), "reason": "cleanup 2"},
        ]
        load = {"state": "NORMAL"}
        
        result = executor.batch_quarantine(candidates, load, verify_safety=False)
        
        self.assertEqual(len(result["executed"]), 2)
        self.assertEqual(len(result["failed"]), 0)
        self.assertGreater(result["total_bytes_recovered"], 0)

    def test_list_quarantine_empty(self):
        items = executor.list_quarantine()
        self.assertEqual(items, [])

    def test_list_quarantine_after_quarantine(self):
        executor.quarantine_file(str(self.test_file), "test reason")
        items = executor.list_quarantine()
        
        self.assertEqual(len(items), 1)
        self.assertIn(str(self.test_file), items[0]["original_path"])
        self.assertEqual(items[0]["reason"], "test reason")

    def test_recovery_stats_empty(self):
        stats = executor.recovery_stats()
        self.assertEqual(stats["total_bytes"], 0)
        self.assertEqual(stats["file_count"], 0)

    def test_recovery_stats_after_quarantine(self):
        executor.quarantine_file(str(self.test_file), "test")
        stats = executor.recovery_stats()
        
        self.assertGreater(stats["total_bytes"], 0)
        self.assertEqual(stats["file_count"], 1)
        self.assertGreaterEqual(stats["integrity_ok"], 0)


if __name__ == "__main__":
    unittest.main()
