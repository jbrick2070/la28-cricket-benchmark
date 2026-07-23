"""Unit tests for metrics calculations, prediction parsing, and schema serialization."""
from __future__ import annotations

import unittest

from la28_cricket.metrics import (
    calculate_brier_score,
    evaluate_model_predictions,
    is_team_match,
    parse_predictions_from_text,
)
from la28_cricket.schema import PredictionRecord, RunMetadata, iso_timestamp


class TestMetricsAndSchema(unittest.TestCase):
    def test_brier_score(self) -> None:
        # Perfect confidence when correct
        self.assertAlmostEqual(calculate_brier_score(100.0, True), 0.0)
        # Total confidence when incorrect
        self.assertAlmostEqual(calculate_brier_score(100.0, False), 1.0)
        # 50% confidence when correct
        self.assertAlmostEqual(calculate_brier_score(50.0, True), 0.25)

    def test_team_matching(self) -> None:
        self.assertTrue(is_team_match("South Africa", "South Africa"))
        self.assertTrue(is_team_match("South Africa [ZA]", "South Africa"))
        self.assertTrue(is_team_match("Great Britain", "England"))
        self.assertFalse(is_team_match("Australia", "India"))

    def test_prediction_parsing(self) -> None:
        sample_text = (
            "What a incredible match! South Africa takes the momentum.\n"
            "NEXT_MATCH_PREDICTION: South Africa — 85%\n"
            "FINAL_PREDICTION: South Africa — 90%\n"
        )
        preds = parse_predictions_from_text(
            text=sample_text,
            model_id="test-model",
            desk_name="Test Desk",
            match_index=1,
            over_index=1,
            timestamp=iso_timestamp(),
        )
        self.assertEqual(len(preds), 2)
        self.assertEqual(preds[0].prediction_type, "NEXT_MATCH")
        self.assertEqual(preds[0].predicted_team, "South Africa")
        self.assertEqual(preds[0].confidence_pct, 85.0)
        self.assertEqual(preds[1].prediction_type, "FINAL")
        self.assertEqual(preds[1].predicted_team, "South Africa")
        self.assertEqual(preds[1].confidence_pct, 90.0)

    def test_evaluation_aggregation(self) -> None:
        preds = [
            PredictionRecord(
                model_id="qwen/qwen2.5-coder-14b",
                desk_name="Desk A",
                prediction_type="NEXT_MATCH",
                predicted_team="South Africa",
                confidence_pct=80.0,
                raw_text="",
                match_index=1,
                over_index=1,
                timestamp="",
            ),
            PredictionRecord(
                model_id="qwen/qwen2.5-coder-14b",
                desk_name="Desk A",
                prediction_type="FINAL",
                predicted_team="South Africa",
                confidence_pct=85.0,
                raw_text="",
                match_index=1,
                over_index=1,
                timestamp="",
            ),
        ]
        eval_summary = evaluate_model_predictions(preds, ["South Africa"], "South Africa")
        self.assertIn("qwen/qwen2.5-coder-14b", eval_summary)
        model_stats = eval_summary["qwen/qwen2.5-coder-14b"]
        self.assertEqual(model_stats["next_match_accuracy_pct"], 100.0)
        self.assertEqual(model_stats["final_winner_accuracy_pct"], 100.0)
        self.assertAlmostEqual(model_stats["mean_brier_score"], 0.04)

    def test_run_metadata_schema(self) -> None:
        meta = RunMetadata(
            run_id="test_run",
            timestamp=iso_timestamp(),
            endpoint="http://10.55.0.2:1234/v1",
            prompt_version="v1.0",
            sampling_baseline={"temperature": 0.2},
            inference_server_hw="Remote RTX 4060",
            client_dashboard_hw="Lenovo RTX 5080",
            models_configured=["m1", "m2"],
            is_dry_run=True,
        )
        d = meta.to_dict()
        self.assertEqual(d["event_type"], "RUN_START")
        self.assertEqual(d["run_id"], "test_run")
        self.assertTrue(d["is_dry_run"])


if __name__ == "__main__":
    unittest.main()
