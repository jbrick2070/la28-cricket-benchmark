#!/usr/bin/env python3
"""Scorecard Import & Historical Prediction Audit Tool.

Imports official 2028 LA28 Cricket match scorecards and evaluates locked model
predictions against real official Olympic match results.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Note: Use `pip install -e .` to setup the package
from la28_cricket.metrics import evaluate_model_predictions
from la28_cricket.schema import PredictionRecord


def load_official_scorecard(scorecard_path: Path) -> List[str]:
    """Load real official match winners list from a JSON scorecard file."""
    if not scorecard_path.exists():
        raise FileNotFoundError(f"Scorecard file not found: {scorecard_path}")

    with scorecard_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return [str(m.get("winner", m)) if isinstance(m, dict) else str(m) for m in data]
    elif isinstance(data, dict) and "match_winners" in data:
        return [str(w) for w in data["match_winners"]]
    else:
        raise ValueError("Invalid scorecard format. Expected list of match objects or {'match_winners': [...]}")


def audit_predictions_against_scorecard(log_path: Path, scorecard_path: Path) -> Dict[str, Any]:
    """Audit locked JSONL predictions against imported official scorecard."""
    if not log_path.exists():
        raise FileNotFoundError(f"Benchmark log file not found: {log_path}")

    official_winners = load_official_scorecard(scorecard_path)
    predictions: List[PredictionRecord] = []
    
    max_match_idx = 0

    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue # Skip malformed lines
                
            if data.get("event_type") == "OVER_EVENT" and data.get("predictions"):
                for p in data["predictions"]:
                    match_idx = int(p["match_index"])
                    max_match_idx = max(max_match_idx, match_idx)
                    predictions.append(
                        PredictionRecord(
                            model_id=p["model_id"],
                            desk_name=p["desk_name"],
                            prediction_type=p["prediction_type"],
                            predicted_team=p["predicted_team"],
                            confidence_pct=float(p["confidence_pct"]),
                            raw_text=p.get("raw_text", ""),
                            match_index=match_idx,
                            over_index=int(p["over_index"]),
                            timestamp=p.get("timestamp", ""),
                        )
                    )
                    
    if max_match_idx > len(official_winners):
        raise ValueError(f"Scorecard has fewer matches ({len(official_winners)}) than predicted in logs (max index {max_match_idx})")

    final_gold = official_winners[-1] if official_winners else "Unknown"
    eval_results = evaluate_model_predictions(
        predictions=predictions,
        actual_match_winners=official_winners,
        final_gold_winner=final_gold,
    )

    return {
        "log_file": str(log_path),
        "scorecard_file": str(scorecard_path),
        "official_match_winners": official_winners,
        "official_gold_winner": final_gold,
        "model_evaluation": eval_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit locked benchmark predictions against official scorecards")
    parser.add_argument("--log-path", required=True, help="Path to locked benchmark JSONL log file")
    parser.add_argument("--scorecard", required=True, help="Path to official 2028 scorecard JSON file")
    parser.add_argument("-o", "--output", help="Output JSON path to write audit results")
    args = parser.parse_args()

    try:
        results = audit_predictions_against_scorecard(Path(args.log_path), Path(args.scorecard))
        
        # Human-readable summary table
        print("=== Official 2028 Scorecard Prediction Audit ===")
        print(f"Log: {results['log_file']}")
        print(f"Scorecard: {results['scorecard_file']}")
        print(f"Gold Medalist: {results['official_gold_winner']}\n")
        
        print(f"{'Model':<30} | {'Brier Score':<12} | {'Matches':<8} | {'Final':<8}")
        print("-" * 65)
        for model_id, stats in results["model_evaluation"].items():
            brier = stats.get("mean_brier_score", 0.0)
            matches_correct = stats.get("total_correct", 0)
            matches_total = stats.get("total_predictions", 0)
            final = stats.get("final_prediction_correct", False)
            print(f"{model_id:<30} | {brier:<12.4f} | {matches_correct}/{matches_total:<5} | {str(final):<8}")
        
        print("\n=== Detailed JSON Results ===")
        print(json.dumps(results, indent=2))
        
        if args.output:
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            print(f"\nAudit results written to {args.output}")
            
        return 0
    except Exception as exc:
        print(f"Error executing scorecard audit: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
