import unittest
from unittest.mock import MagicMock, patch

from aegisstore import storage_intelligence


class StorageIntelligenceTests(unittest.TestCase):
    def test_forecast_quality_insufficient(self):
        quality = storage_intelligence.assess_forecast_quality(2)
        self.assertEqual(quality, "INSUFFICIENT")

    def test_forecast_quality_low(self):
        quality = storage_intelligence.assess_forecast_quality(4)
        self.assertEqual(quality, "LOW")

    def test_forecast_quality_medium(self):
        quality = storage_intelligence.assess_forecast_quality(7)
        self.assertEqual(quality, "MEDIUM")

    def test_forecast_quality_high(self):
        quality = storage_intelligence.assess_forecast_quality(15)
        self.assertEqual(quality, "HIGH")

    def test_format_growth_rate_bytes(self):
        rate = storage_intelligence.format_growth_rate(512)
        self.assertIn("B/day", rate)

    def test_format_growth_rate_mb(self):
        rate = storage_intelligence.format_growth_rate(1024 * 1024 * 5)
        self.assertIn("MB/day", rate)

    def test_format_growth_rate_gb(self):
        rate = storage_intelligence.format_growth_rate(1024 ** 3 * 2.1)
        self.assertIn("+2.1", rate)
        self.assertIn("GB/day", rate)

    def test_format_growth_rate_negative(self):
        rate = storage_intelligence.format_growth_rate(-(1024 ** 3))
        self.assertIn("-1", rate)
        self.assertIn("GB/day", rate)

    def test_human_bytes_gb(self):
        result = storage_intelligence.human_bytes(1024 ** 3 * 8.7)
        self.assertIn("GB", result)

    def test_no_historical_data(self):
        with patch("aegisstore.storage_intelligence.predictor.forecast", return_value=None):
            result = storage_intelligence.storage_forecast_detailed("/demo_disk")
            self.assertIsNone(result["forecast"])
            self.assertEqual(result["forecast_quality"], "INSUFFICIENT")
            self.assertIn("historical data", result["recommendation"])

    def test_low_growth(self):
        mock_forecast = {
            "current_usage_pct": 0.62,
            "growth_rate_bytes_per_day": 1024 * 100,
            "growth_rate_gb_per_day": 0.0001,
            "sample_count": 5,
            "predictions_days": {0.85: None, 0.90: None, 0.95: None},
        }
        with patch("aegisstore.storage_intelligence.predictor.forecast", return_value=mock_forecast):
            result = storage_intelligence.storage_forecast_detailed("/demo_disk")
            self.assertIn("minimal", result["recommendation"])

    def test_negative_growth(self):
        mock_forecast = {
            "current_usage_pct": 0.62,
            "growth_rate_bytes_per_day": -1024 ** 3,
            "growth_rate_gb_per_day": -1.0,
            "sample_count": 8,
            "predictions_days": {0.85: None, 0.90: None, 0.95: None},
        }
        with patch("aegisstore.storage_intelligence.predictor.forecast", return_value=mock_forecast):
            result = storage_intelligence.storage_forecast_detailed("/demo_disk")
            self.assertIn("shrinking", result["recommendation"])


if __name__ == "__main__":
    unittest.main()
