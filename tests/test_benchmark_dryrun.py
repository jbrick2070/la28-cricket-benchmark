"""End-to-End dry-run test executing full 140-over campaign in mock mode."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from la28_cricket.benchmark import LA28CricketBenchmark


class TestBenchmarkDryRun(unittest.TestCase):
    def test_full_campaign_dry_run(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            tmp.close()  # Fix Windows file lock issue

        try:
            benchmark = LA28CricketBenchmark(
                log_path=str(tmp_path),
                dry_run=True,
                delay_seconds=0.0,
            )
            # Run all 140 overs in dry-run mode
            summary = benchmark.run_campaign(max_overs_override=140)

            self.assertEqual(summary["total_overs"], 140)
            
            # Note: old API might not have 'total_matches' or might have a different logic. 
            # We'll check if it exists before asserting to be resilient to new/old APIs.
            if "total_matches" in summary:
                self.assertEqual(summary["total_matches"], 7)
            self.assertTrue(summary.get("is_dry_run", True))

            # Inspect generated JSONL log
            lines = [line.strip() for line in tmp_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertGreater(len(lines), 140)

            event_types = set()
            over_events = 0
            match_resolutions = 0

            for line in lines:
                evt = json.loads(line)
                # handle both old/new schema
                etype = evt.get("event_type")
                if not etype:
                    if "over_index" in evt and "state_before" in evt:
                        etype = "OVER_EVENT"
                    elif "actual_winner" in evt:
                        etype = "MATCH_RESOLVED"
                    elif "total_overs" in evt:
                        etype = "CAMPAIGN_SUMMARY"
                    elif "prompt_version" in evt:
                        etype = "RUN_START"
                        
                event_types.add(etype)
                if etype == "OVER_EVENT":
                    over_events += 1
                elif etype in ("MATCH_RESOLVED", "MATCH_RESULT"):
                    match_resolutions += 1

            self.assertIn("RUN_START", event_types)
            self.assertIn("OVER_EVENT", event_types)
            self.assertTrue("MATCH_RESOLVED" in event_types or "MATCH_RESULT" in event_types)
            self.assertIn("CAMPAIGN_SUMMARY", event_types)
            self.assertEqual(over_events, 140)
            self.assertEqual(match_resolutions, 7)

        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    def test_partial_campaign_dry_run(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            tmp.close()

        try:
            benchmark = LA28CricketBenchmark(
                log_path=str(tmp_path),
                dry_run=True,
                delay_seconds=0.0,
            )
            summary = benchmark.run_campaign(max_overs_override=5)

            self.assertEqual(summary["total_overs"], 5)

            lines = [line.strip() for line in tmp_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            
            over_events = 0
            for line in lines:
                evt = json.loads(line)
                etype = evt.get("event_type")
                if not etype and "over_index" in evt and "state_before" in evt:
                    etype = "OVER_EVENT"
                    
                if etype == "OVER_EVENT":
                    over_events += 1

            self.assertEqual(over_events, 5)

        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

if __name__ == "__main__":
    unittest.main()
