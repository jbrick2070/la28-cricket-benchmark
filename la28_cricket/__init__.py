"""LA28 Women's Cricket LLM Benchmark Package."""
from __future__ import annotations

__version__ = "1.1.0"

from la28_cricket.benchmark import LA28CricketBenchmark
from la28_cricket.config import (
    DEFAULT_ENDPOINT,
    PREFERRED_MODEL_A,
    PREFERRED_MODEL_B,
    SCHEDULE,
    TEAM_CODES,
)

__all__ = [
    "LA28CricketBenchmark",
    "DEFAULT_ENDPOINT",
    "PREFERRED_MODEL_A",
    "PREFERRED_MODEL_B",
    "SCHEDULE",
    "TEAM_CODES",
    "__version__",
]
