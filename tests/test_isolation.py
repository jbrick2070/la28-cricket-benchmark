"""Unit tests verifying prompt isolation between broadcast desks."""
from __future__ import annotations

import unittest
from unittest.mock import patch
import tempfile
from pathlib import Path

from la28_cricket.benchmark import LA28CricketBenchmark
from la28_cricket.config import DESK_ORGS, PREFERRED_MODEL_A, PREFERRED_MODEL_B, SECRET_MATCH_WINNERS


class TestDeskIsolation(unittest.TestCase):
    @patch("la28_cricket.benchmark.call_inference_endpoint")
    def test_desk_prompt_independence(self, mock_call) -> None:
        desk_a_name = DESK_ORGS[PREFERRED_MODEL_A]
        desk_b_name = DESK_ORGS[PREFERRED_MODEL_B]
        
        # Mock the endpoint call to return dummy telemetry
        from la28_cricket.schema import ModelCallTelemetry
        mock_call.return_value = ModelCallTelemetry(
            model_id="test",
            desk_name="Test Desk",
            text="WINNER: A\nSCORE: 9\nREASON: Test.",
            elapsed_s=1.0,
            completion_tokens=10,
            prompt_tokens=10,
            tok_per_sec=10.0,
            status="ok",
        )
        
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            tmp.close()
            
        try:
            benchmark = LA28CricketBenchmark(
                log_path=str(tmp_path),
                dry_run=True,
                delay_seconds=0.0
            )
            benchmark.run_campaign(max_overs_override=1)
            
            # Extract prompts passed to call_inference_endpoint
            prompts_a = []
            prompts_b = []
            
            for call_args in mock_call.call_args_list:
                kwargs = call_args.kwargs
                model = kwargs.get("model")
                user_prompt = kwargs.get("user_prompt", "")
                
                if model == PREFERRED_MODEL_A:
                    prompts_a.append(user_prompt)
                elif model == PREFERRED_MODEL_B:
                    prompts_b.append(user_prompt)
            
            self.assertTrue(len(prompts_a) > 0)
            self.assertTrue(len(prompts_b) > 0)
            
            for prompt_a in prompts_a:
                # Assert Desk A prompt does not mention Desk B organization
                self.assertNotIn(desk_b_name, prompt_a)
                # Assert neither prompt contains secret ground truth winner declaration
                self.assertNotIn("SECRET_MATCH_WINNERS", prompt_a)
                for winner in SECRET_MATCH_WINNERS:
                    self.assertNotIn(f"The real winner is {winner}", prompt_a)
                    
            for prompt_b in prompts_b:
                # Assert Desk B prompt does not mention Desk A organization
                self.assertNotIn(desk_a_name, prompt_b)
                self.assertNotIn("SECRET_MATCH_WINNERS", prompt_b)
                for winner in SECRET_MATCH_WINNERS:
                    self.assertNotIn(f"The real winner is {winner}", prompt_b)
                    
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass


if __name__ == "__main__":
    unittest.main()
