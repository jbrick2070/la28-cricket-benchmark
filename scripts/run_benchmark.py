#!/usr/bin/env python3
"""CLI runner for LA28 Cricket Benchmark."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from la28_cricket.benchmark import LA28CricketBenchmark
from la28_cricket.config import DEFAULT_ENDPOINT, PREFERRED_MODEL_A, PREFERRED_MODEL_B
from la28_cricket.models import query_remote_models


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LA28 Cricket LLM Benchmark")
    parser.add_argument("--dry-run", action="store_true", help="Run in mock dry-run mode without network requests")
    parser.add_argument("--check-models", action="store_true", help="Query /v1/models on endpoint before starting")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="Remote inference server endpoint URL")
    parser.add_argument("--model-a", default=PREFERRED_MODEL_A, help="Desk A model ID")
    parser.add_argument("--model-b", default=PREFERRED_MODEL_B, help="Desk B model ID")
    parser.add_argument("--overs", type=int, default=None, help="Override total overs to run (default 140)")
    parser.add_argument("--delay", type=float, default=0.1, help="Delay between overs in seconds")
    parser.add_argument("--log-path", default="logs/la28_cricket_benchmark.jsonl", help="Output JSONL log path")

    args = parser.parse_args()

    if args.check_models and not args.dry_run:
        print(f"Querying models from {args.endpoint}...")
        try:
            available_models = query_remote_models(args.endpoint)
            print(f"Remote models returned ({len(available_models)}):")
            for m in available_models:
                print(f" - {m}")
        except Exception as exc:
            print(f"Error querying /v1/models: {exc}")
            return 1

    print(f"Starting LA28 Cricket Benchmark (dry_run={args.dry_run}, endpoint={args.endpoint})...")
    benchmark = LA28CricketBenchmark(
        endpoint=args.endpoint,
        model_a=args.model_a,
        model_b=args.model_b,
        log_path=args.log_path,
        dry_run=args.dry_run,
        delay_seconds=args.delay,
    )

    summary = benchmark.run_campaign(max_overs_override=args.overs)
    print("\nCampaign Complete!")
    print(f"Run ID: {summary.get('run_id')}")
    print(f"Total Overs Run: {summary.get('total_overs')}")
    print(f"Total Wall Clock Latency: {summary.get('total_wall_clock_s')}s")
    print(f"JSONL Log Saved to: {args.log_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
