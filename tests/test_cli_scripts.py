import sys
import json
import os
import unittest
from pathlib import Path
import subprocess

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)


class TestCLIScripts(unittest.TestCase):
    def _run_script(self, script_name, *args):
        """Run a script in scripts/ with PYTHONPATH set to the project root."""
        script_path = Path(PROJECT_ROOT) / "scripts" / script_name
        env = os.environ.copy()
        env["PYTHONPATH"] = PROJECT_ROOT + os.pathsep + env.get("PYTHONPATH", "")
        return subprocess.run(
            [sys.executable, str(script_path)] + list(args),
            capture_output=True, text=True, env=env, timeout=120,
        )

    def test_run_benchmark_dry_run(self):
        res = self._run_script("run_benchmark.py", "--dry-run", "--overs", "5", "--delay", "0")
        self.assertEqual(res.returncode, 0, f"stderr: {res.stderr}\nstdout: {res.stdout}")
        self.assertIn("Campaign Complete!", res.stdout)

    def test_verify_remote_endpoint_failure(self):
        res = self._run_script("verify_remote_endpoint.py", "--endpoint", "http://127.0.0.1:9999/v1")
        # return code 1 for connection failure
        self.assertEqual(res.returncode, 1, f"stderr: {res.stderr}\nstdout: {res.stdout}")
        # Script prints ERROR with details
        self.assertIn("ERROR", res.stdout)

    def test_import_official_scorecard(self):
        fixture_path = Path(PROJECT_ROOT) / "tests" / "fixtures" / "sample_scorecard.json"

        # Create a dummy jsonl file with correct prediction_type values
        log_path = Path(PROJECT_ROOT) / "tests" / "fixtures" / "dummy_log.jsonl"
        with open(log_path, "w") as f:
            f.write(json.dumps({
                "event_type": "OVER_EVENT",
                "predictions": [{
                    "model_id": "test_model",
                    "desk_name": "Test Desk",
                    "prediction_type": "NEXT_MATCH",
                    "predicted_team": "South Africa",
                    "confidence_pct": 85.0,
                    "raw_text": "",
                    "match_index": 1,
                    "over_index": 1,
                    "timestamp": ""
                }]
            }) + "\n")

        try:
            res = self._run_script("import_official_scorecard.py", "--log-path", str(log_path), "--scorecard", str(fixture_path))
            self.assertEqual(res.returncode, 0, f"stderr: {res.stderr}\nstdout: {res.stdout}")
        finally:
            if log_path.exists():
                log_path.unlink()

    def test_help_flags(self):
        for script in ["run_benchmark.py", "verify_remote_endpoint.py", "import_official_scorecard.py"]:
            res = self._run_script(script, "--help")
            self.assertEqual(res.returncode, 0, f"{script} --help failed: {res.stderr}")
            self.assertIn("usage:", res.stdout.lower())


if __name__ == "__main__":
    unittest.main()
