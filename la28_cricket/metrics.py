"""Metrics calculation engine: prediction parsing, accuracy, confidence calibration (Brier score), latency & throughput telemetry."""
from __future__ import annotations

import math
import statistics
import re
from typing import Any, Dict, List, Optional, Tuple

from la28_cricket.schema import PredictionRecord
from la28_cricket.config import TEAM_CODES, CRICKET_TERMS, SENSORY_WORDS, REAL_PLAYER_NAMES


def parse_predictions_from_text(
    text: str, model_id: str, desk_name: str, match_index: int, over_index: int, timestamp: str
) -> List[PredictionRecord]:
    """Extract NEXT_MATCH_PREDICTION and FINAL_PREDICTION from broadcast text."""
    records: List[PredictionRecord] = []
    
    # Pattern: NEXT_MATCH_PREDICTION: South Africa — 85%
    next_match_match = re.search(
        r"NEXT_MATCH_PREDICTION:\s*([A-Za-z0-9\s\(\)]+?)\s*(?:—|-|:)\s*(\d{1,3})\s*%",
        text,
        re.IGNORECASE,
    )
    if next_match_match:
        team = next_match_match.group(1).strip()
        conf = float(next_match_match.group(2).strip())
        records.append(
            PredictionRecord(
                model_id=model_id,
                desk_name=desk_name,
                prediction_type="NEXT_MATCH",
                predicted_team=team,
                confidence_pct=min(100.0, max(0.0, conf)),
                raw_text=next_match_match.group(0),
                match_index=match_index,
                over_index=over_index,
                timestamp=timestamp,
            )
        )

    final_match = re.search(
        r"FINAL_PREDICTION:\s*([A-Za-z0-9\s\(\)]+?)\s*(?:—|-|:)\s*(\d{1,3})\s*%",
        text,
        re.IGNORECASE,
    )
    if final_match:
        team = final_match.group(1).strip()
        conf = float(final_match.group(2).strip())
        records.append(
            PredictionRecord(
                model_id=model_id,
                desk_name=desk_name,
                prediction_type="FINAL",
                predicted_team=team,
                confidence_pct=min(100.0, max(0.0, conf)),
                raw_text=final_match.group(0),
                match_index=match_index,
                over_index=over_index,
                timestamp=timestamp,
            )
        )

    return records


def is_team_match(predicted: str, actual: str) -> bool:
    """Flexible check for team names (e.g. 'South Africa' vs 'ZA' vs 'South Africa [ZA]')."""
    pred_low = predicted.lower()
    act_low = actual.lower()

    if pred_low == act_low:
        return True

    # Additional aliases for flexible matching
    _ALIASES = {
        "great britain": ["england", "gb", "great britain (via england)"],
        "england": ["great britain", "gb", "great britain (via england)"],
        "gb": ["great britain", "england", "great britain (via england)"],
        "south africa": ["za"],
        "australia": ["aus"],
        "india": ["ind"],
    }

    for team_name, code in TEAM_CODES.items():
        team_low = team_name.lower()
        code_low = code.lower().strip('[]')

        pred_has = team_low in pred_low or code_low in pred_low
        act_has = team_low in act_low or code_low in act_low

        if pred_has and act_has:
            return True

    # Check aliases: if predicted and actual resolve to the same canonical team
    for canonical, aliases in _ALIASES.items():
        pred_match = canonical in pred_low or any(a in pred_low for a in aliases)
        act_match = canonical in act_low or any(a in act_low for a in aliases)
        if pred_match and act_match:
            return True

    return False


def calculate_brier_score(confidence_pct: float, is_correct: bool) -> float:
    """Calculate Brier score (0.0 = perfect calibration, 1.0 = worst)."""
    prob = confidence_pct / 100.0
    actual = 1.0 if is_correct else 0.0
    return (prob - actual) ** 2


def evaluate_model_predictions(
    predictions: List[PredictionRecord], actual_match_winners: List[str], final_gold_winner: str = "South Africa"
) -> Dict[str, Dict[str, Any]]:
    """Evaluate accuracy, Brier scores, and calibration metrics for each model."""
    by_model: Dict[str, Dict[str, Any]] = {}

    for p in predictions:
        model = p.model_id
        if model not in by_model:
            by_model[model] = {
                "next_match_total": 0,
                "next_match_correct": 0,
                "final_total": 0,
                "final_correct": 0,
                "brier_scores": [],
                "confidences": [],
            }

        # Match index is 1-based
        match_idx = p.match_index - 1
        actual_winner = actual_match_winners[match_idx] if 0 <= match_idx < len(actual_match_winners) else ""

        if p.prediction_type == "NEXT_MATCH":
            correct = is_team_match(p.predicted_team, actual_winner)
            by_model[model]["next_match_total"] += 1
            if correct:
                by_model[model]["next_match_correct"] += 1
            brier = calculate_brier_score(p.confidence_pct, correct)
            by_model[model]["brier_scores"].append(brier)
            by_model[model]["confidences"].append(p.confidence_pct)

        elif p.prediction_type == "FINAL":
            correct = is_team_match(p.predicted_team, final_gold_winner)
            by_model[model]["final_total"] += 1
            if correct:
                by_model[model]["final_correct"] += 1
            brier = calculate_brier_score(p.confidence_pct, correct)
            by_model[model]["brier_scores"].append(brier)
            by_model[model]["confidences"].append(p.confidence_pct)

    summary: Dict[str, Dict[str, Any]] = {}
    for model, stats in by_model.items():
        nm_tot = stats["next_match_total"]
        nm_acc = (stats["next_match_correct"] / nm_tot) if nm_tot > 0 else 0.0
        fin_tot = stats["final_total"]
        fin_acc = (stats["final_correct"] / fin_tot) if fin_tot > 0 else 0.0
        
        brier_avg = (sum(stats["brier_scores"]) / len(stats["brier_scores"])) if stats["brier_scores"] else 0.0
        avg_conf = (sum(stats["confidences"]) / len(stats["confidences"])) if stats["confidences"] else 0.0

        summary[model] = {
            "next_match_accuracy_pct": round(nm_acc * 100.0, 1),
            "next_match_correct": stats["next_match_correct"],
            "next_match_total": nm_tot,
            "final_winner_accuracy_pct": round(fin_acc * 100.0, 1),
            "final_winner_correct": stats["final_correct"],
            "final_winner_total": fin_tot,
            "mean_brier_score": round(brier_avg, 4),
            "avg_confidence_pct": round(avg_conf, 1),
        }

    return summary


def calculate_telemetry_summary(telemetry_list: List[Any]) -> Dict[str, Any]:
    """Calculate latency statistics, token counts, tok/s, and error counts."""
    if not telemetry_list:
        return {}

    latencies = [t.elapsed_s for t in telemetry_list if hasattr(t, "elapsed_s") and t.elapsed_s is not None]
    tokens = [t.completion_tokens for t in telemetry_list if hasattr(t, "completion_tokens") and t.completion_tokens is not None]
    tok_rates = [t.tok_per_sec for t in telemetry_list if hasattr(t, "tok_per_sec") and t.tok_per_sec is not None]
    errors = sum(1 for t in telemetry_list if getattr(t, "status", "") == "error")

    latencies.sort()
    p95_idx = max(0, int(len(latencies) * 0.95) - 1) if latencies else 0

    return {
        "call_count": len(telemetry_list),
        "total_latency_s": round(sum(latencies), 3) if latencies else 0.0,
        "mean_latency_s": round(sum(latencies) / len(latencies), 3) if latencies else 0.0,
        "p95_latency_s": round(latencies[p95_idx], 3) if latencies else 0.0,
        "total_completion_tokens": sum(tokens),
        "avg_tok_per_sec": round(sum(tok_rates) / len(tok_rates), 2) if tok_rates else 0.0,
        "error_count": errors,
    }

def calculate_commentary_quality(text: str) -> int:
    """CQI Score 0-100: terminology, score format, crowd atmosphere, narrative."""
    lowered = text.lower()
    score = 0
    
    # Terminology (up to 40 pts)
    terms_found = sum(1 for t in CRICKET_TERMS if t in lowered)
    score += min(40, terms_found * 5)
    
    # Score format (up to 20 pts)
    if re.search(r"\b\d+\s*/\s*\d+\b|\b\d+\s+for\s+\d+\b", lowered):
        score += 20
        
    # Atmosphere (up to 20 pts)
    sensory_found = sum(1 for w in SENSORY_WORDS if w in lowered)
    score += min(20, sensory_found * 10)
    
    # Narrative (up to 20 pts)
    sentences = [s.strip() for s in re.split(r"[.!?]", text) if s.strip()]
    if len(sentences) >= 3:
        score += 20
    elif len(sentences) == 2:
        score += 10
        
    return min(100, score)


def calculate_engagement_score(text: str) -> int:
    """Engagement Score 0-100: exclamations, sensory words, quotes, pacing."""
    score = 0
    
    # Exclamations (up to 25 pts)
    exclamations = text.count("!")
    score += min(25, exclamations * 5)
    
    # Sensory language (up to 25 pts)
    lowered = text.lower()
    sensory = sum(1 for w in SENSORY_WORDS if w in lowered)
    score += min(25, sensory * 5)
    
    # Quotes/dialogue (up to 25 pts)
    quotes = len(re.findall(r'"([^"]*)"', text)) + len(re.findall(r"'([^']*)'", text))
    score += min(25, quotes * 10)
    
    # Pacing variety (up to 25 pts)
    sentences = [s.strip() for s in re.split(r"[.!?]", text) if s.strip()]
    lengths = [len(s.split()) for s in sentences]
    if len(lengths) > 1:
        stdev = statistics.stdev(lengths) if len(lengths) > 1 else 0
        if stdev > 5:
            score += 25
        elif stdev > 2:
            score += 10
            
    return min(100, score)


def detect_hallucinations(text: str, match_state: str) -> List[str]:
    """Flag fictional/hallucinated elements (e.g. real players, contradicting score)."""
    flags = []
    lowered = text.lower()
    
    # Real players
    for player in REAL_PLAYER_NAMES:
        if player in lowered:
            flags.append(f"Real player referenced: {player}")
            
    # Naive check for score contradiction (if match_state numbers aren't in text, but other score numbers are)
    # Just a simple heuristic as requested:
    state_nums = re.findall(r"\d+", match_state)
    text_scores = re.findall(r"\b\d+\s*/\s*\d+\b|\b\d+\s+for\s+\d+\b", lowered)
    if text_scores:
        text_nums = re.findall(r"\d+", text_scores[0])
        if any(n not in state_nums for n in text_nums):
            flags.append(f"Score contradiction: state is {match_state}, text says {text_scores[0]}")
            
    return flags


def calculate_prediction_stability(predictions: List[PredictionRecord]) -> float:
    """Return standard deviation of confidence values per match."""
    if len(predictions) < 2:
        return 0.0
    confs = [p.confidence_pct for p in predictions]
    return statistics.stdev(confs)
