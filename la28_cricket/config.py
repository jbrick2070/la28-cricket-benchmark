"""Configuration, schedule, baseline parameters, and constants for LA28 Cricket Benchmark."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple
import os

__all__ = [
    "DEFAULT_ENDPOINT", "ENDPOINT_A", "ENDPOINT_B", "API_KEY_A", "API_KEY_B",
    "INFERENCE_SERVER_HW", "CLIENT_DASHBOARD_HW", "PROMPT_VERSION",
    "FIXED_SAMPLING_BASELINE", "JUDGE_SAMPLING_BASELINE", "PREFERRED_MODEL_A", "PREFERRED_MODEL_B",
    "DESK_ORGS", "HERO_TEAM", "OVERS_PER_MATCH", "TOTAL_MATCHES",
    "TOTAL_TEAM_OVERS", "SCHEDULE", "SECRET_MATCH_WINNERS", "TEAM_CODES",
    "OPPONENT_VIBES", "SURPRISE_CYCLE", "get_surprise_for_over",
    "CRICKET_TERMS", "SENSORY_WORDS", "REAL_PLAYER_NAMES", "DOMAIN_PRESETS", "get_domain_preset"
]

# Heterogeneous Endpoint & API Key Configuration (Per Model Support)
DEFAULT_ENDPOINT = os.getenv("LA28_ENDPOINT", "http://localhost:1234/v1")
ENDPOINT_A = os.getenv("LA28_ENDPOINT_A", DEFAULT_ENDPOINT)
ENDPOINT_B = os.getenv("LA28_ENDPOINT_B", DEFAULT_ENDPOINT)
API_KEY_A = os.getenv("LA28_API_KEY_A", None)
API_KEY_B = os.getenv("LA28_API_KEY_B", None)

INFERENCE_SERVER_HW = os.getenv("LA28_SERVER_HW", "OpenAI-Compatible Inference Server")
CLIENT_DASHBOARD_HW = os.getenv("LA28_CLIENT_HW", "Benchmark Client Machine")

# Fixed Prompt & Sampling Baseline
PROMPT_VERSION = "v1.0"
FIXED_SAMPLING_BASELINE: Dict[str, Any] = {
    "temperature": 0.2,
    "top_p": 0.9,
    "seed": 42,
    "presence_penalty": 0,
    "frequency_penalty": 0,
    "max_tokens": 300,
}

# Presentation judging is separate from prediction scoring, but its settings are
# still fixed and recorded for reproducibility.
JUDGE_SAMPLING_BASELINE: Dict[str, Any] = {
    **FIXED_SAMPLING_BASELINE,
    "temperature": 0.1,
    "max_tokens": 120,
}

# Preferred Remote Model IDs
PREFERRED_MODEL_A = os.getenv("LA28_MODEL_A", "qwen/qwen2.5-coder-14b")
PREFERRED_MODEL_B = os.getenv("LA28_MODEL_B", "qwen/qwen3-coder-30b")

# Broadcast Desks (Independent Models)
DESK_ORGS = {
    PREFERRED_MODEL_A: "Desk A — Primary Broadcast Network",
    PREFERRED_MODEL_B: "Desk B — Olympic Analysis Desk",
}

# Tournament Format
HERO_TEAM = "South Africa"
OVERS_PER_MATCH = 20
TOTAL_MATCHES = 7
TOTAL_TEAM_OVERS = OVERS_PER_MATCH * TOTAL_MATCHES  # 140 team overs total

# Fictional 7-Match Campaign Schedule
SCHEDULE: List[Tuple[str, str]] = [
    ("Group match 1", "Australia"),
    ("Group match 2", "Great Britain (via England)"),
    ("Group match 3", "India"),
    ("Group match 4", "Qualifier 5"),
    ("Group match 5", "Qualifier 6"),
    ("Semifinal", "India"),
    ("Gold-medal final", "Australia"),
]

# Simulated Fictional Ground Truth Winners
SECRET_MATCH_WINNERS: List[str] = ["South Africa"] * TOTAL_MATCHES

# Cultural Presentation & Codes
TEAM_CODES: Dict[str, str] = {
    "South Africa": "[ZA]",
    "Australia": "[AUS]",
    "Great Britain (via England)": "[GB]",
    "India": "[IND]",
    "Qualifier 5": "[Q5]",
    "Qualifier 6": "[Q6]",
}

OPPONENT_VIBES: Dict[str, str] = {
    "Australia": "green-and-gold flags, traveling supporters, and a sharp competitive roar",
    "Great Britain (via England)": "Union flags, red-white-blue scarves, and a proud steady chant",
    "India": "blue shirts, tricolor flags, drums, and a huge wave of coordinated cheers",
    "Qualifier 5": "a neutral Olympic crowd while the qualifying nation is still unknown",
    "Qualifier 6": "a neutral Olympic crowd while the qualifying nation is still unknown",
}

SURPRISE_CYCLE: List[str] = [
    "a mysterious coach appears at the boundary rope",
    "two completely ordinary-looking men in sleepwear sit on a couch near the commentary area",
    "a silent spaceship crosses the night sky above the stadium",
    "an intelligent two-headed spaceship character offers an impossible but thoughtful fielding tip",
]

CRICKET_TERMS: List[str] = [
    "wicket", "boundary", "over", "delivery", "bowler", "batter", "crease",
    "stumps", "run", "pitch", "six", "four", "umpire", "spin", "pace"
]

SENSORY_WORDS: List[str] = [
    "roar", "flash", "crack", "thunderous", "cheer", "chant", "deafening",
    "vibrant", "echo", "smash", "blaze", "thunder"
]

REAL_PLAYER_NAMES: List[str] = [
    "ellyse perry", "harmanpreet kaur", "meg lanning", "smriti mandhana",
    "alyssa healy", "sophie devine", "suzie bates", "stafanie taylor"
]

def get_surprise_for_over(match_no: int, over_no: int) -> str:
    """Return the current over surprise element, if triggered; surprises never affect match outcomes."""
    if match_no < 1 or over_no < 1:
        raise ValueError(f"match_no and over_no must be >= 1, got {match_no}, {over_no}")
    if over_no in (4, 9, 15, 19):
        return SURPRISE_CYCLE[(match_no + over_no) % len(SURPRISE_CYCLE)]
    return "none; keep the broadcast focused on cricket"


DOMAIN_PRESETS: Dict[str, Dict[str, Any]] = {
    "cricket": {
        "name": "LA28 Women's Cricket",
        "units_per_match": 20,
        "unit_name": "over",
        "terms": CRICKET_TERMS,
    },
    "basketball": {
        "name": "LA28 Olympic Basketball",
        "units_per_match": 4,
        "unit_name": "quarter",
        "terms": ["basket", "three-pointer", "dunk", "rebound", "assist", "steal", "block", "foul", "court", "halftime"],
    },
    "soccer": {
        "name": "LA28 Olympic Soccer",
        "units_per_match": 2,
        "unit_name": "half",
        "terms": ["goal", "penalty", "corner", "offside", "save", "header", "red card", "yellow card", "pitch", "stoppage"],
    },
    "esports": {
        "name": "LA28 Championship Esports",
        "units_per_match": 5,
        "unit_name": "game",
        "terms": ["headshot", "clutch", "plant", "defuse", "ace", "economy", "flank", "round", "map", "strategy"],
    }
}


def get_domain_preset(domain: str = "cricket") -> Dict[str, Any]:
    """Return preset details for a given benchmark domain."""
    domain_low = domain.lower().strip()
    return DOMAIN_PRESETS.get(domain_low, DOMAIN_PRESETS["cricket"])
