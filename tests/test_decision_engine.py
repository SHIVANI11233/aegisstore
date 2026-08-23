import unittest

from aegisstore.decision_engine import assess


class DecisionEngineRiskScoreTests(unittest.TestCase):
    def test_low_risk_candidate_is_automated(self):
        candidate = {
            "classification": "Cold + Redundant",
            "confidence": 0.95,
            "duplicate_of": "/tmp/dup.zip",
            "age_days": 143,
            "size_bytes": 40 * 1024 * 1024,
        }
        ctx = {
            "active_process": False,
            "package_owned": False,
            "git_tracked": False,
        }
        load = {"cpu_percent": 34, "io_wait_percent": 2, "memory_percent": 61}

        decision = assess(candidate, ctx, load, False)

        self.assertIn("risk_score", decision)
        self.assertIn("risk_tier", decision)
        self.assertIn("action", decision)
        self.assertIn("factors", decision)
        self.assertEqual(decision["risk_tier"], "LOW")
        self.assertEqual(decision["action"], "AUTOMATE")
        self.assertLessEqual(decision["risk_score"], 30)
        self.assertTrue(any("duplicate" in factor.lower() for factor in decision["factors"]))

    def test_busy_system_defers_clean_up(self):
        candidate = {
            "classification": "Cold",
            "confidence": 0.95,
            "duplicate_of": None,
            "age_days": 90,
            "size_bytes": 10 * 1024 * 1024,
        }
        ctx = {
            "active_process": False,
            "package_owned": False,
            "git_tracked": False,
        }
        load = {"cpu_percent": 91, "io_wait_percent": 22, "memory_percent": 84}

        decision = assess(candidate, ctx, load, True)

        self.assertEqual(decision["action"], "DEFER")
        self.assertTrue(any("busy" in factor.lower() or "high cpu" in factor.lower() or "high i/o" in factor.lower()
                            for factor in decision["factors"]))

    def test_active_process_is_skipped(self):
        candidate = {
            "classification": "Cold",
            "confidence": 0.99,
            "duplicate_of": None,
            "age_days": 50,
            "size_bytes": 5 * 1024 * 1024,
        }
        ctx = {
            "active_process": True,
            "package_owned": False,
            "git_tracked": False,
        }
        load = {"cpu_percent": 20, "io_wait_percent": 1, "memory_percent": 30}

        decision = assess(candidate, ctx, load, False)

        self.assertEqual(decision["action"], "SKIP")
        self.assertEqual(decision["risk_score"], 100)
        self.assertEqual(decision["risk_tier"], "HIGH")


if __name__ == "__main__":
    unittest.main()
