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

        try:
            benchmark = LA28CricketBenchmark(
                log_path=str(tmp_path),
                dry_run=True,
                delay_seconds=0.0,
            )
            # Run all 140 overs in dry-run mode
            summary = benchmark.run_campaign(max_overs_override=140)

            self.assertEqual(summary["total_overs"], 140)
            self.assertEqual(summary["total_matches"], 7)
            self.assertTrue(summary["is_dry_run"])

            # Inspect generated JSONL log
            lines = [line.strip() for line in tmp_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertGreater(len(lines), 140)

            event_types = set()
            over_events = 0
            match_resolutions = 0

            for line in lines:
                evt = json.loads(line)
                etype = evt.get("event_type")
                event_types.add(etype)
                if etype == "OVER_EVENT":
                    over_events += 1
                elif etype == "MATCH_RESOLVED":
                    match_resolutions += 1

            self.assertIn("RUN_START", event_types)
            self.assertIn("OVER_EVENT", event_types)
            self.assertIn("MATCH_RESOLVED", event_types)
            self.assertIn("CAMPAIGN_SUMMARY", event_types)
            self.assertEqual(over_events, 140)
            self.assertEqual(match_resolutions, 7)

        finally:
            if tmp_path.exists():
                tmp_path.unlink()


if __name__ == "__main__":
    unittest.main()
