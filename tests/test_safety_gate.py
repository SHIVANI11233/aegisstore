import unittest
from unittest.mock import patch

from aegisstore import decision_engine, safety_gate


class SafetyGateTests(unittest.TestCase):
    def test_normal_state(self):
        state = safety_gate.classify_system_state(60, 70, 5)
        self.assertEqual(state, "NORMAL")

    def test_busy_state(self):
        state = safety_gate.classify_system_state(80, 70, 8)
        self.assertEqual(state, "BUSY")

    def test_critical_state(self):
        state = safety_gate.classify_system_state(92, 85, 22)
        self.assertEqual(state, "CRITICAL")

    def test_windows_iowait_unavailable(self):
        with patch("aegisstore.safety_gate.psutil.cpu_times_percent", side_effect=Exception("no iowait")):
            self.assertEqual(safety_gate._resolve_io_wait(), 0.0)

    def test_cpu_threshold(self):
        self.assertEqual(safety_gate.classify_system_state(75, 30, 0), "BUSY")

    def test_ram_threshold(self):
        self.assertEqual(safety_gate.classify_system_state(60, 80, 0), "BUSY")

    def test_io_wait_threshold(self):
        self.assertEqual(safety_gate.classify_system_state(60, 50, 10), "BUSY")

    def test_live_safety_override_user_visible(self):
        load = {"cpu_percent": 93, "memory_percent": 87, "io_wait_percent": 21, "state": "CRITICAL"}
        self.assertTrue(safety_gate.is_system_busy(load))

    def test_low_file_risk_critical_system_defer(self):
        candidate = {"classification": "Cold + Redundant", "confidence": 0.95, "duplicate_of": "/tmp/dup.zip", "age_days": 143}
        ctx = {"active_process": False, "package_owned": False, "git_tracked": False}
        load = {"cpu_percent": 93, "memory_percent": 87, "io_wait_percent": 21, "state": "CRITICAL"}
        decision = decision_engine.assess(candidate, ctx, load, True)
        self.assertEqual(decision["action"], "DEFER")
        self.assertEqual(decision["risk_tier"], "LOW")


if __name__ == "__main__":
    unittest.main()
