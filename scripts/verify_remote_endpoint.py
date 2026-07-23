#!/usr/bin/env python3
"""Endpoint verification tool to query /v1/models on RTX 4060 and check local 5080 resident status."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from la28_cricket.config import DEFAULT_ENDPOINT, PREFERRED_MODEL_A, PREFERRED_MODEL_B
from la28_cricket.models import query_remote_models


def check_local_5080_status() -> None:
    """Inspect local LM Studio status using lms ps --json if lms CLI is installed."""
    lms_bin = shutil.which("lms")
    if not lms_bin:
        print("[5080 Local Check] 'lms' CLI tool not found in PATH; skipping local status query.")
        return

    try:
        res = subprocess.run([lms_bin, "ps", "--json"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            print("[5080 Local Check] Resident Local LM Studio Models:")
            print(res.stdout)
        else:
            print(f"[5080 Local Check] lms ps returned code {res.returncode}: {res.stderr}")
    except Exception as exc:
        print(f"[5080 Local Check] Failed to query local lms status: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify remote endpoint & model availability")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="Remote inference endpoint URL")
    args = parser.parse_args()

    print(f"=== LA28 Cricket Benchmark Health Check ===")
    print(f"Target Remote Endpoint: {args.endpoint}")

    try:
        remote_models = query_remote_models(args.endpoint)
        print(f"\n[4060 Remote Endpoint] Query successful! Found {len(remote_models)} available models:")
        for m in remote_models:
            is_pref = " (PREFERRED)" if m in (PREFERRED_MODEL_A, PREFERRED_MODEL_B) else ""
            print(f"  - {m}{is_pref}")

        missing = []
        if PREFERRED_MODEL_A not in remote_models:
            missing.append(PREFERRED_MODEL_A)
        if PREFERRED_MODEL_B not in remote_models:
            missing.append(PREFERRED_MODEL_B)

        if missing:
            print(f"\nWARNING: Missing preferred benchmark models on remote endpoint: {missing}")
        else:
            print("\nSUCCESS: All preferred benchmark model IDs are present on remote 4060 server.")
    except Exception as exc:
        print(f"\nERROR: Failed to connect to remote 4060 endpoint at {args.endpoint}: {exc}")

    print("\n--- Local Environment Status ---")
    check_local_5080_status()
    print("\nHealth check complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
