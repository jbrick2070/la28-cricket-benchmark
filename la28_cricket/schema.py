"""Structured JSONL schema definitions for benchmark logging, provenance, and auditability."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def iso_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RunMetadata:
    run_id: str
    timestamp: str
    endpoint: str
    prompt_version: str
    sampling_baseline: Dict[str, Any]
    inference_server_hw: str
    client_dashboard_hw: str
    models_configured: List[str]
    is_dry_run: bool = False
    endpoints_by_role: Dict[str, str] = field(default_factory=dict)
    judge_sampling_baseline: Dict[str, Any] = field(default_factory=dict)
    log_path: Optional[str] = None
    format_version: str = "1.1"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["event_type"] = "RUN_START"
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RunMetadata:
        d = dict(data)
        d.pop("event_type", None)
        return cls(**d)


@dataclass
class PredictionRecord:
    model_id: str
    desk_name: str
    prediction_type: str  # "NEXT_MATCH" or "FINAL"
    predicted_team: str
    confidence_pct: float
    raw_text: str
    match_index: int
    over_index: int
    timestamp: str

    def __post_init__(self):
        self.confidence_pct = max(0.0, min(100.0, float(self.confidence_pct)))
        if self.prediction_type not in ("NEXT_MATCH", "FINAL"):
            raise ValueError(f"Invalid prediction_type: {self.prediction_type}")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PredictionRecord:
        return cls(**data)


@dataclass
class ModelCallTelemetry:
    model_id: str
    desk_name: str
    text: str
    elapsed_s: float
    completion_tokens: Optional[int]
    prompt_tokens: Optional[int]
    tok_per_sec: Optional[float]
    status: str  # "ok" or "error"
    error: Optional[str] = None
    endpoint: Optional[str] = None
    attempt_count: int = 1
    requested_sampling: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OverQualityMetrics:
    cqi_score: int
    engagement_score: int
    hallucination_flags: List[str]
    prediction_stability: float


@dataclass
class OverEventRecord:
    timestamp: str
    run_id: str
    match_index: int
    over_index: int
    phase: str
    hero_team: str
    opponent_team: str
    state_before: str
    telemetry: List[ModelCallTelemetry]
    predictions: List[PredictionRecord]
    judge_model: str
    judge_verdict: str
    judge_elapsed_s: float
    winner_model: Optional[str]
    state_after: Dict[str, int]
    quality_metrics: Dict[str, OverQualityMetrics] = field(default_factory=dict)
    judge_telemetry: Optional[ModelCallTelemetry] = None
    candidate_call_order: List[str] = field(default_factory=list)
    surprise: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["event_type"] = "OVER_EVENT"
        return data


@dataclass
class MatchResultRecord:
    run_id: str
    timestamp: str
    match_index: int
    phase: str
    opponent: str
    actual_winner: str
    predictions_evaluation: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["event_type"] = "MATCH_RESOLVED"
        return data


@dataclass
class CampaignSummaryRecord:
    run_id: str
    timestamp: str
    total_matches: int
    total_overs: int
    total_wall_clock_s: float
    metrics_per_model: Dict[str, Dict[str, Any]]
    is_dry_run: bool
    completion_status: str = "completed"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["event_type"] = "CAMPAIGN_SUMMARY"
        return data
