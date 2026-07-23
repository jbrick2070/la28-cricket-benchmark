#!/usr/bin/env python3
"""Endpoint verification tool to query /v1/models on RTX 4060 and check local 5080 resident status."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Note: Use `pip install -e .` to install la28_cricket package

from la28_cricket.config import DEFAULT_ENDPOINT, PREFERRED_MODEL_A, PREFERRED_MODEL_B
from la28_cricket.models import query_remote_models


def check_local_5080_status(json_output=False) -> dict | None:
    """Inspect local LM Studio status using lms ps --json if lms CLI is installed."""
    lms_bin = shutil.which("lms")
    if not lms_bin:
        if not json_output:
            print("[5080 Local Check] 'lms' CLI tool not found in PATH; skipping local status query.")
        return None

    try:
        res = subprocess.run([lms_bin, "ps", "--json"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            if not json_output:
                print("[5080 Local Check] Resident Local LM Studio Models:")
                print(res.stdout)
            import json
            return json.loads(res.stdout)
        else:
            if not json_output:
                print(f"[5080 Local Check] lms ps returned code {res.returncode}: {res.stderr}")
    except Exception as exc:
        if not json_output:
            print(f"[5080 Local Check] Failed to query local lms status: {exc}")
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify remote endpoint & model availability")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="Remote inference endpoint URL")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    if not args.json:
        print("=== LA28 Cricket Benchmark Health Check ===")
        print(f"Target Remote Endpoint: {args.endpoint}")

    out_dict = {"endpoint": args.endpoint, "status": "unknown", "models": [], "missing": []}

    try:
        remote_models = query_remote_models(args.endpoint)
        out_dict["models"] = remote_models
        
        if not args.json:
            print(f"\n[4060 Remote Endpoint] Query successful! Found {len(remote_models)} available models:")
            for m in remote_models:
                is_pref = " (PREFERRED)" if m in (PREFERRED_MODEL_A, PREFERRED_MODEL_B) else ""
                print(f"  - {m}{is_pref}")

        missing = []
        if PREFERRED_MODEL_A not in remote_models:
            missing.append(PREFERRED_MODEL_A)
        if PREFERRED_MODEL_B not in remote_models:
            missing.append(PREFERRED_MODEL_B)
            
        out_dict["missing"] = missing

        if missing:
            if not args.json:
                print(f"\nWARNING: Missing preferred benchmark models on remote endpoint: {missing}")
            out_dict["status"] = "missing_models"
        else:
            if not args.json:
                print("\nSUCCESS: All preferred benchmark model IDs are present on remote 4060 server.")
            out_dict["status"] = "ok"

    except Exception as exc:
        if not args.json:
            print(f"\nERROR: Failed to connect to remote 4060 endpoint at {args.endpoint}: {exc}")
        out_dict["status"] = "error"
        out_dict["error_message"] = str(exc)

    if not args.json:
        print("\n--- Local Environment Status ---")
        
    local_status = check_local_5080_status(args.json)
    out_dict["local_status"] = local_status

    if not args.json:
        print("\nHealth check complete.")
        
    if args.json:
        import json
        print(json.dumps(out_dict, indent=2))

    if out_dict["status"] == "error":
        return 1
    if out_dict["status"] == "missing_models":
        return 2
        
    return 0


if __name__ == "__main__":
    sys.exit(main())
