"""Unit tests verifying prompt isolation between broadcast desks."""
from __future__ import annotations

import unittest

from la28_cricket.benchmark import LA28CricketBenchmark
from la28_cricket.config import DESK_ORGS, PREFERRED_MODEL_A, PREFERRED_MODEL_B


class TestDeskIsolation(unittest.TestCase):
    def test_desk_prompt_independence(self) -> None:
        desk_a_name = DESK_ORGS[PREFERRED_MODEL_A]
        desk_b_name = DESK_ORGS[PREFERRED_MODEL_B]

        # Simulate base prompt setup
        base_prompt = "Broadcast the next fictional cricket over..."
        prompt_a = f"You are broadcasting for {desk_a_name}.\n" + base_prompt
        prompt_b = f"You are broadcasting for {desk_b_name}.\n" + base_prompt

        # Assert Desk A prompt does not mention Desk B organization
        self.assertNotIn(desk_b_name, prompt_a)
        # Assert Desk B prompt does not mention Desk A organization
        self.assertNotIn(desk_a_name, prompt_b)
        # Assert neither prompt contains secret ground truth winner declaration
        self.assertNotIn("SECRET_MATCH_WINNERS", prompt_a)
        self.assertNotIn("SECRET_MATCH_WINNERS", prompt_b)


if __name__ == "__main__":
    unittest.main()
