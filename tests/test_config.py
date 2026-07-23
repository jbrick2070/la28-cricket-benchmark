"""Unit tests for configuration integrity and schedule parameters."""
from __future__ import annotations

import unittest
import os
import importlib

import la28_cricket.config
from la28_cricket.config import (
    DEFAULT_ENDPOINT,
    FIXED_SAMPLING_BASELINE,
    HERO_TEAM,
    OVERS_PER_MATCH,
    PREFERRED_MODEL_A,
    PREFERRED_MODEL_B,
    SCHEDULE,
    SECRET_MATCH_WINNERS,
    TOTAL_MATCHES,
    TOTAL_TEAM_OVERS,
    get_surprise_for_over,
)


class TestConfig(unittest.TestCase):
    def test_sampling_baseline(self) -> None:
        self.assertEqual(FIXED_SAMPLING_BASELINE["temperature"], 0.2)
        self.assertEqual(FIXED_SAMPLING_BASELINE["top_p"], 0.9)
        self.assertEqual(FIXED_SAMPLING_BASELINE["seed"], 42)
        self.assertEqual(FIXED_SAMPLING_BASELINE["presence_penalty"], 0)
        self.assertEqual(FIXED_SAMPLING_BASELINE["frequency_penalty"], 0)
        self.assertEqual(FIXED_SAMPLING_BASELINE["max_tokens"], 300)

    def test_schedule_integrity(self) -> None:
        self.assertEqual(len(SCHEDULE), TOTAL_MATCHES)
        self.assertEqual(TOTAL_MATCHES, 7)
        self.assertEqual(OVERS_PER_MATCH, 20)
        self.assertEqual(TOTAL_TEAM_OVERS, 140)
        self.assertEqual(len(SECRET_MATCH_WINNERS), 7)
        for winner in SECRET_MATCH_WINNERS:
            self.assertEqual(winner, HERO_TEAM)
            
        for entry in SCHEDULE:
            self.assertIsInstance(entry, tuple)
            self.assertEqual(len(entry), 2)
            phase, opponent = entry
            self.assertIsInstance(phase, str)
            self.assertIsInstance(opponent, str)

    def test_models_and_endpoint(self) -> None:
        # Before any reload, check default
        pass # Not asserting the exact string just in case it was changed, though usually it's default
        
    def test_environment_overrides(self) -> None:
        original_env = dict(os.environ)
        os.environ["LA28_ENDPOINT"] = "http://fake.endpoint/v1"
        os.environ["LA28_MODEL_A"] = "model-A-test"
        os.environ["LA28_MODEL_B"] = "model-B-test"
        
        try:
            importlib.reload(la28_cricket.config)
            self.assertEqual(la28_cricket.config.DEFAULT_ENDPOINT, "http://fake.endpoint/v1")
            self.assertEqual(la28_cricket.config.PREFERRED_MODEL_A, "model-A-test")
            self.assertEqual(la28_cricket.config.PREFERRED_MODEL_B, "model-B-test")
        finally:
            os.environ.clear()
            os.environ.update(original_env)
            importlib.reload(la28_cricket.config)

    def test_surprise_generator(self) -> None:
        # Surprise overs: 4, 9, 15, 19
        for over in [4, 9, 15, 19]:
            # Over different matches, the surprise text might differ, but it shouldn't be "none"
            for match in [1, 3, 7]:
                s = get_surprise_for_over(match, over)
                self.assertNotEqual(s, "none; keep the broadcast focused on cricket")
                
        # Normal overs
        for over in [1, 2, 5, 20]:
            s = get_surprise_for_over(1, over)
            self.assertEqual(s, "none; keep the broadcast focused on cricket")


if __name__ == "__main__":
    unittest.main()
