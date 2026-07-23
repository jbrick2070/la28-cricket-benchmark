#!/usr/bin/env python3
"""CLI runner for LA28 Cricket Benchmark."""
from __future__ import annotations

import argparse
import sys
import threading
import json
from pathlib import Path

# Note: Use `pip install -e .` to setup the package
from la28_cricket.benchmark import LA28CricketBenchmark
from la28_cricket.config import DEFAULT_ENDPOINT, PREFERRED_MODEL_A, PREFERRED_MODEL_B


class CLIReportingBenchmark(LA28CricketBenchmark):
    def __init__(self, verbose_output=False, no_color=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.verbose_output = verbose_output
        self.no_color = no_color
        
    def _write_record(self, record_dict):
        super()._write_record(record_dict)
        
        # Simple colors if allowed
        c_reset = "" if self.no_color else "\033[0m"
        c_green = "" if self.no_color else "\033[92m"
        c_cyan = "" if self.no_color else "\033[96m"
        c_yellow = "" if self.no_color else "\033[93m"
        c_bold = "" if self.no_color else "\033[1m"
        
        event_type = record_dict.get("event_type", "")
        # Fallback for old API if event_type not explicitly in dict but inferred from structure
        if not event_type:
            if "over_index" in record_dict and "state_before" in record_dict:
                event_type = "OVER_EVENT"
            elif "actual_winner" in record_dict:
                event_type = "MATCH_RESULT"
            elif "total_overs" in record_dict:
                event_type = "CAMPAIGN_SUMMARY"
        
        if event_type == "OVER_EVENT":
            m_idx = record_dict.get("match_index", "?")
            o_idx = record_dict.get("over_index", "?")
            state = record_dict.get("state_after", {})
            runs = state.get("runs", 0)
            wkts = state.get("wickets", 0)
            
            # Unicode box drawing scoreboard
            print(f"{c_bold}╔════════════════════════════════════════════════════════════════════════╗{c_reset}")
            print(f"{c_bold}║{c_reset} {c_cyan}Match {m_idx}{c_reset} | {c_yellow}Over {o_idx}{c_reset} | Score: {c_green}{runs}/{wkts}{c_reset}".ljust(85) + f"{c_bold}║{c_reset}")
            print(f"{c_bold}╚════════════════════════════════════════════════════════════════════════╝{c_reset}")
            
            if self.verbose_output:
                verdict = record_dict.get("judge_verdict", "").strip().replace("\n", " ")
                print(f"   Judge Verdict: {verdict}")
                preds = record_dict.get("predictions", [])
                if preds:
                    print(f"   Predictions found: {len(preds)}")
                    
    def get_partial_summary(self):
        """Generate a basic partial summary if interrupted."""
        return {
            "run_id": getattr(self, "run_id", "unknown"),
            "status": "interrupted",
            "log_path": str(getattr(self, "log_path", "unknown"))
        }

def start_obs_server(port):
    try:
        from la28_cricket.obs_overlays import start_server
        print(f"Starting OBS overlay server on port {port}...")
        server_thread = threading.Thread(target=start_server, args=(port,), daemon=True)
        server_thread.start()
    except ImportError as e:
        print(f"WARNING: Could not import OBS overlay server: {e}")

def main() -> int:
    parser = argparse.ArgumentParser(description="Run LA28 Cricket LLM Benchmark")
    parser.add_argument("--dry-run", action="store_true", help="Run in mock dry-run mode without network requests")
    parser.add_argument("--check-models", action="store_true", help="Query /v1/models on endpoint before starting")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="Remote inference server endpoint URL")
    parser.add_argument("--endpoint-a", default=None, help="Specific endpoint URL for Desk A (overrides --endpoint)")
    parser.add_argument("--endpoint-b", default=None, help="Specific endpoint URL for Desk B (overrides --endpoint)")
    parser.add_argument("--api-key-a", default=None, help="API Key for Desk A model endpoint")
    parser.add_argument("--api-key-b", default=None, help="API Key for Desk B model endpoint")
    parser.add_argument("--model-a", default=PREFERRED_MODEL_A, help="Desk A model ID")
    parser.add_argument("--model-b", default=PREFERRED_MODEL_B, help="Desk B model ID")
    parser.add_argument("--domain", default="cricket", choices=["cricket", "basketball", "soccer", "esports"], help="Benchmark domain preset")
    parser.add_argument("--overs", type=int, default=None, help="Override total overs to run")
    parser.add_argument("--delay", type=float, default=0.1, help="Delay between overs in seconds")
    parser.add_argument("--log-path", default="logs/la28_cricket_benchmark.jsonl", help="Output JSONL log path")
    parser.add_argument("--verbose", action="store_true", help="Print detailed per-over output")
    parser.add_argument("--obs-port", type=int, default=None, help="Start OBS overlay server on this port")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI color output")

    args = parser.parse_args()

    if args.check_models:
        if args.dry_run:
            print("WARNING: --check-models is silently skipped in --dry-run mode.")
        else:
            ep = args.endpoint_a or args.endpoint
            print(f"Querying models from {ep}...")
            try:
                from la28_cricket.models import query_remote_models
                available_models = query_remote_models(ep)
                print(f"Remote models returned ({len(available_models)}):")
                for m in available_models:
                    print(f" - {m}")
            except Exception as exc:
                print(f"Error querying /v1/models: {exc}")
                return 1

    log_path = Path(args.log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    if args.obs_port:
        start_obs_server(args.obs_port)

    print(f"Starting LA28 Universal LLM Benchmark (domain={args.domain}, dry_run={args.dry_run}, endpoint={args.endpoint})...")
    benchmark = CLIReportingBenchmark(
        verbose_output=args.verbose,
        no_color=args.no_color,
        endpoint=args.endpoint,
        endpoint_a=args.endpoint_a,
        endpoint_b=args.endpoint_b,
        api_key_a=args.api_key_a,
        api_key_b=args.api_key_b,
        domain=args.domain,
        model_a=args.model_a,
        model_b=args.model_b,
        log_path=str(log_path),
        dry_run=args.dry_run,
        delay_seconds=args.delay,
    )

    try:
        summary = benchmark.run_campaign(max_overs_override=args.overs)
        print("\nCampaign Complete!")
        print(f"Run ID: {summary.get('run_id')}")
        print(f"Total Overs Run: {summary.get('total_overs')}")
        print(f"Total Wall Clock Latency: {summary.get('total_wall_clock_s', 'N/A')}s")
        print(f"JSONL Log Saved to: {args.log_path}")
    except KeyboardInterrupt:
        print("\n\n[!] Campaign interrupted by user (KeyboardInterrupt).")
        partial = benchmark.get_partial_summary()
        print(f"Run ID: {partial.get('run_id')}")
        print(f"Status: {partial.get('status')}")
        print(f"Partial JSONL Log Saved to: {args.log_path}")
        return 130

    return 0

if __name__ == "__main__":
    sys.exit(main())
