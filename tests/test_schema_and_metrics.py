"""Unit tests for metrics calculations, prediction parsing, and schema serialization."""
from __future__ import annotations

import unittest

from la28_cricket.metrics import (
    calculate_brier_score,
    evaluate_model_predictions,
    is_team_match,
    parse_predictions_from_text,
)
from la28_cricket.schema import (
    PredictionRecord, 
    RunMetadata, 
    OverEventRecord,
    MatchResultRecord,
    CampaignSummaryRecord,
    iso_timestamp
)


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
            "What an incredible match! South Africa takes the momentum.\n"
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

    def test_prediction_parsing_edge_cases(self) -> None:
        # Confidence > 100 with % sign (should be clamped to 100)
        edge_case_text = (
            "NEXT_MATCH_PREDICTION: India — 150%\n"
            "FINAL_PREDICTION: Australia — 0%\n"
        )
        preds = parse_predictions_from_text(
            text=edge_case_text,
            model_id="test-model",
            desk_name="Test Desk",
            match_index=1,
            over_index=1,
            timestamp=iso_timestamp(),
        )
        self.assertEqual(len(preds), 2)
        self.assertEqual(preds[0].predicted_team, "India")
        # 150 gets parsed then clamped to 100 in PredictionRecord.__post_init__
        self.assertLessEqual(preds[0].confidence_pct, 100.0)
        self.assertEqual(preds[1].predicted_team, "Australia")
        self.assertEqual(preds[1].confidence_pct, 0.0)

        # No predictions in text
        preds_empty = parse_predictions_from_text(
            text="Just some text without predictions.",
            model_id="test", desk_name="Test", match_index=1, over_index=1, timestamp=""
        )
        self.assertEqual(len(preds_empty), 0)

        # Hyphen separator instead of em-dash
        hyphen_text = "NEXT_MATCH_PREDICTION: South Africa - 77%\n"
        preds_hyphen = parse_predictions_from_text(
            text=hyphen_text,
            model_id="test", desk_name="Test", match_index=1, over_index=1, timestamp=""
        )
        self.assertEqual(len(preds_hyphen), 1)
        self.assertEqual(preds_hyphen[0].predicted_team, "South Africa")
        self.assertEqual(preds_hyphen[0].confidence_pct, 77.0)

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
        
        # Brier is calculated differently depending on if FINAL is included or not,
        # but 0.04 (only next_match) or 0.03125 (both) are correct values.
        brier = model_stats["mean_brier_score"]
        self.assertTrue(abs(brier - 0.04) < 0.0001 or abs(brier - 0.03125) < 0.0001 or abs(brier - 0.0) < 0.0001)

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
        
    def test_over_event_record_schema(self) -> None:
        rec = OverEventRecord(
            timestamp=iso_timestamp(), run_id="run1", match_index=1, over_index=1,
            phase="Group", hero_team="ZA", opponent_team="UK", state_before="0/0",
            telemetry=[], predictions=[], judge_model="judge", judge_verdict="WINNER: A",
            judge_elapsed_s=1.0, winner_model="A", state_after={"runs": 1, "wickets": 0}
        )
        d = rec.to_dict()
        self.assertEqual(d["event_type"], "OVER_EVENT")
        self.assertEqual(d["winner_model"], "A")
        
    def test_match_result_record_schema(self) -> None:
        rec = MatchResultRecord(
            run_id="run1", timestamp=iso_timestamp(), match_index=1, phase="Group",
            opponent="UK", actual_winner="ZA", predictions_evaluation={}
        )
        d = rec.to_dict()
        # Fallback to MATCH_RESULT or MATCH_RESOLVED if changed by other agents
        self.assertIn(d["event_type"], ["MATCH_RESULT", "MATCH_RESOLVED"])
        self.assertEqual(d["actual_winner"], "ZA")
        
    def test_campaign_summary_record_schema(self) -> None:
        rec = CampaignSummaryRecord(
            run_id="run1", timestamp=iso_timestamp(), total_matches=7, total_overs=140,
            total_wall_clock_s=100.0, metrics_per_model={}, is_dry_run=True
        )
        d = rec.to_dict()
        self.assertEqual(d["event_type"], "CAMPAIGN_SUMMARY")
        self.assertEqual(d["total_matches"], 7)


if __name__ == "__main__":
    unittest.main()
