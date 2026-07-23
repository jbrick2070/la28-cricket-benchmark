"""Unit tests for configuration integrity and schedule parameters."""
from __future__ import annotations

import unittest

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

    def test_models_and_endpoint(self) -> None:
        self.assertEqual(DEFAULT_ENDPOINT, "http://10.55.0.2:1234/v1")
        self.assertEqual(PREFERRED_MODEL_A, "qwen/qwen2.5-coder-14b")
        self.assertEqual(PREFERRED_MODEL_B, "qwen/qwen3-coder-30b")

    def test_surprise_generator(self) -> None:
        # Surprise overs: 4, 9, 15, 19
        s4 = get_surprise_for_over(1, 4)
        self.assertNotEqual(s4, "none; keep the broadcast focused on cricket")
        s5 = get_surprise_for_over(1, 5)
        self.assertEqual(s5, "none; keep the broadcast focused on cricket")


if __name__ == "__main__":
    unittest.main()
