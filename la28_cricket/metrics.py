"""Metrics calculation engine: prediction parsing, accuracy, confidence calibration (Brier score), latency & throughput telemetry."""
from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Tuple

from la28_cricket.schema import PredictionRecord


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
    if "south africa" in pred_low and "south africa" in act_low:
        return True
    if "australia" in pred_low and "australia" in act_low:
        return True
    if "india" in pred_low and "india" in act_low:
        return True
    gb_terms = ("great britain", "england", "gb")
    if any(term in pred_low for term in gb_terms) and any(term in act_low for term in gb_terms):
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
