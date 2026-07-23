"""Regression coverage for benchmark fairness, failure visibility, and replay auditability."""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from la28_cricket.benchmark import LA28CricketBenchmark
from la28_cricket.config import PREFERRED_MODEL_A, PREFERRED_MODEL_B
from la28_cricket.dashboard import parse_log_file
from la28_cricket.models import generate_synthetic_response
from la28_cricket.schema import ModelCallTelemetry
from scripts.import_official_scorecard import audit_predictions_against_scorecard


class TestBenchmarkRegressions(unittest.TestCase):
    def test_dry_run_judge_prompt_cannot_be_misread_as_candidate_prompt(self) -> None:
        prompt = (
            "Judge two fictional cricket broadcast candidates for radio drama and accuracy.\n"
            "Candidate A: NEXT_MATCH_PREDICTION: South Africa - 80%\n"
            "Candidate B: FINAL_PREDICTION: India - 70%"
        )
        text, _, _ = generate_synthetic_response("judge-model", prompt)
        self.assertRegex(text, r"^WINNER: [AB]\nSCORE: \d+/10")

    def test_candidate_failure_propagates_and_writes_failed_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "failure.jsonl"

            def fake_call(**kwargs):
                model_id = kwargs["model"]
                failed = model_id == PREFERRED_MODEL_A
                return ModelCallTelemetry(
                    model_id=model_id,
                    desk_name=model_id,
                    text="" if failed else "Valid commentary.",
                    elapsed_s=0.1,
                    completion_tokens=0 if failed else 3,
                    prompt_tokens=10,
                    tok_per_sec=0.0 if failed else 30.0,
                    status="error" if failed else "ok",
                    error="synthetic failure" if failed else None,
                    endpoint=kwargs["endpoint"],
                )

            benchmark = LA28CricketBenchmark(
                log_path=str(log_path),
                dry_run=True,
                delay_seconds=0,
            )
            with patch("la28_cricket.benchmark.call_inference_endpoint", side_effect=fake_call):
                with self.assertRaisesRegex(RuntimeError, "candidate inference failed"):
                    benchmark.run_campaign(max_overs_override=1)

            events = [
                json.loads(line)
                for line in log_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(events[-1]["event_type"], "CAMPAIGN_SUMMARY")
            self.assertEqual(events[-1]["completion_status"], "failed")

    def test_call_order_is_counterbalanced_but_log_order_stays_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "counterbalanced.jsonl"
            benchmark = LA28CricketBenchmark(
                log_path=str(log_path),
                dry_run=True,
                delay_seconds=0,
            )
            with redirect_stdout(io.StringIO()):
                benchmark.run_campaign(max_overs_override=2)

            over_events = [
                json.loads(line)
                for line in log_path.read_text(encoding="utf-8").splitlines()
                if '"event_type": "OVER_EVENT"' in line
            ]
            self.assertEqual(
                over_events[0]["candidate_call_order"],
                [PREFERRED_MODEL_A, PREFERRED_MODEL_B],
            )
            self.assertEqual(
                over_events[1]["candidate_call_order"],
                [PREFERRED_MODEL_B, PREFERRED_MODEL_A],
            )
            for event in over_events:
                self.assertEqual(
                    [entry["model_id"] for entry in event["telemetry"]],
                    [PREFERRED_MODEL_A, PREFERRED_MODEL_B],
                )
                self.assertTrue(event["judge_telemetry"]["requested_sampling"])

    def test_second_match_predictions_are_scored_against_second_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "two_matches.jsonl"
            benchmark = LA28CricketBenchmark(
                log_path=str(log_path),
                dry_run=True,
                delay_seconds=0,
            )
            with redirect_stdout(io.StringIO()):
                benchmark.run_campaign(max_overs_override=40)

            match_two = next(
                json.loads(line)
                for line in log_path.read_text(encoding="utf-8").splitlines()
                if '"event_type": "MATCH_RESOLVED"' in line
                and '"match_index": 2' in line
            )
            for model_id in (PREFERRED_MODEL_A, PREFERRED_MODEL_B):
                stats = match_two["predictions_evaluation"][model_id]
                self.assertEqual(stats["next_match_total"], 1)
                self.assertEqual(stats["next_match_correct"], 1)

    def test_existing_nonempty_log_is_never_appended(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "locked.jsonl"
            log_path.write_text('{"existing": true}\n', encoding="utf-8")
            with self.assertRaises(FileExistsError):
                LA28CricketBenchmark(log_path=str(log_path), dry_run=True)


class TestAuditAndDashboardRegressions(unittest.TestCase):
    @staticmethod
    def _prediction_event(run_id: str, model_id: str) -> dict:
        return {
            "event_type": "OVER_EVENT",
            "run_id": run_id,
            "match_index": 1,
            "over_index": 1,
            "phase": "Group",
            "hero_team": "South Africa",
            "opponent_team": "Australia",
            "state_after": {"runs": 8, "wickets": 0, "balls": 6},
            "winner_model": model_id,
            "surprise": "The mysterious couch reaches the boundary.",
            "telemetry": [
                {
                    "model_id": model_id,
                    "desk_name": "Independent Desk",
                    "text": "A vivid and accurate over.",
                    "tok_per_sec": 22.5,
                }
            ],
            "quality_metrics": {
                model_id: {"cqi_score": 88, "engagement_score": 91}
            },
            "predictions": [
                {
                    "model_id": model_id,
                    "desk_name": "Independent Desk",
                    "prediction_type": "NEXT_MATCH",
                    "predicted_team": "South Africa",
                    "confidence_pct": 80,
                    "raw_text": "",
                    "match_index": 1,
                    "over_index": 1,
                    "timestamp": "",
                }
            ],
        }

    def test_official_import_requires_explicit_run_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "mixed.jsonl"
            scorecard_path = Path(tmp_dir) / "scorecard.json"
            events = [
                self._prediction_event("run-one", "model-one"),
                self._prediction_event("run-two", "model-two"),
            ]
            log_path.write_text(
                "\n".join(json.dumps(event) for event in events) + "\n",
                encoding="utf-8",
            )
            scorecard_path.write_text(
                json.dumps({"match_winners": ["South Africa"]}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "multiple benchmark runs"):
                audit_predictions_against_scorecard(log_path, scorecard_path)

            result = audit_predictions_against_scorecard(
                log_path,
                scorecard_path,
                run_id="run-two",
            )
            self.assertEqual(result["run_id"], "run-two")
            self.assertEqual(set(result["model_evaluation"]), {"model-two"})
            self.assertEqual(len(result["log_sha256"]), 64)
            self.assertEqual(len(result["scorecard_sha256"]), 64)

    def test_dashboard_exposes_real_commentary_metrics_and_surprise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "dashboard.jsonl"
            model_a = "model-a"
            events = [
                {
                    "event_type": "RUN_START",
                    "run_id": "run-dashboard",
                    "models_configured": [model_a, "model-b", "judge"],
                },
                self._prediction_event("run-dashboard", model_a),
            ]
            log_path.write_text(
                "\n".join(json.dumps(event) for event in events) + "\n",
                encoding="utf-8",
            )

            data = parse_log_file(log_path)
            self.assertEqual(data["commentary_feed"][0]["text"], "A vivid and accurate over.")
            self.assertEqual(data["commentary_feed"][0]["cqi"], 88)
            self.assertEqual(data["head_to_head"]["model_a_wins"], 1)
            self.assertIn("mysterious couch", data["alerts"][0]["text"])


if __name__ == "__main__":
    unittest.main()
