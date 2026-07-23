"""Standalone local web dashboard for LA28 Cricket Benchmark monitoring (built with Python http.server)."""
from __future__ import annotations

import argparse
import json
import http.server
import socketserver
import sys
from pathlib import Path
from typing import Any, Dict, List

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LA28 Women's Cricket LLM Benchmark Dashboard</title>
    <style>
        :root {
            --bg-color: #0b0f19;
            --card-bg: #161f33;
            --accent-gold: #f59e0b;
            --accent-green: #10b981;
            --accent-blue: #3b82f6;
            --accent-purple: #8b5cf6;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --border-color: #1e293b;
        }

        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 20px;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 20px;
            border-bottom: 2px solid var(--border-color);
            margin-bottom: 20px;
        }

        .header h1 {
            margin: 0;
            font-size: 1.8rem;
            color: var(--accent-gold);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .badge {
            background: #2563eb;
            color: white;
            font-size: 0.8rem;
            padding: 4px 8px;
            border-radius: 4px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .card {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
        }

        .card h2 {
            margin-top: 0;
            font-size: 1.2rem;
            color: var(--accent-blue);
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 8px;
        }

        .metric-value {
            font-size: 2rem;
            font-weight: bold;
            color: var(--text-main);
        }

        .metric-label {
            color: var(--text-muted);
            font-size: 0.9rem;
        }

        .prediction-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }

        .prediction-table th, .prediction-table td {
            padding: 8px 12px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }

        .prediction-table th {
            color: var(--accent-gold);
        }

        .footer {
            margin-top: 30px;
            padding-top: 15px;
            border-top: 1px solid var(--border-color);
            font-size: 0.85rem;
            color: var(--text-muted);
            display: flex;
            justify-content: space-between;
        }

        .disclaimer {
            background: #1e1b4b;
            border-left: 4px solid var(--accent-purple);
            padding: 12px;
            margin-bottom: 20px;
            border-radius: 4px;
            font-size: 0.9rem;
        }
    </style>
</head>
<body>

<div class="header">
    <h1>🏏 LA28 Women's Cricket Benchmark <span class="badge">Simulated Ground Truth</span></h1>
    <div style="text-align: right;">
        <span id="run-status">Monitoring Live Logs...</span>
    </div>
</div>

<div class="disclaimer">
    <strong>Benchmark Disclaimer:</strong> This is a fictional LA28 women's cricket LLM simulation. Match outcomes are simulated ground truth only. There is no official LA28 cricket winner until the real 2028 Olympic matches take place.
</div>

<div class="grid">
    <div class="card">
        <h2>Match State</h2>
        <div class="metric-value" id="current-score">0/0</div>
        <div class="metric-label" id="current-match">Match 1: South Africa vs Australia</div>
        <p><strong id="current-phase">Group match 1</strong> | Over <span id="current-over">0</span> / 20</p>
    </div>

    <div class="card">
        <h2>Telemetry & Speed</h2>
        <p><strong>Inference Server:</strong> Remote RTX 4060 (10.55.0.2)</p>
        <p><strong>Dashboard Client:</strong> Lenovo RTX 5080</p>
        <p><strong>Desk A (Qwen2.5):</strong> <span id="desk-a-toks">0</span> tok/s (<span id="desk-a-lat">0</span>s)</p>
        <p><strong>Desk B (Qwen3):</strong> <span id="desk-b-toks">0</span> tok/s (<span id="desk-b-lat">0</span>s)</p>
    </div>

    <div class="card">
        <h2>Model Accuracy & Calibration</h2>
        <table class="prediction-table">
            <thead>
                <tr>
                    <th>Model</th>
                    <th>Match Acc</th>
                    <th>Final Acc</th>
                    <th>Brier Score</th>
                </tr>
            </thead>
            <tbody id="metrics-body">
                <tr><td colspan="4">Awaiting completed overs...</td></tr>
            </tbody>
        </table>
    </div>
</div>

<div class="card">
    <h2>Broadcast Desk Predictions (Over 1 Pre-Game)</h2>
    <div id="predictions-container">Awaiting match predictions...</div>
</div>

<div class="footer">
    <div>Endpoint: http://10.55.0.2:1234/v1 | Baseline: temp=0.2, top_p=0.9, seed=42</div>
    <div>OBS: Optional Adapter Only</div>
</div>

<script>
    async function updateDashboard() {
        try {
            const resp = await fetch('/api/data');
            const data = await resp.json();
            
            if (data.latest_over) {
                document.getElementById('current-score').innerText = data.latest_over.state_after.runs + '/' + data.latest_over.state_after.wickets;
                document.getElementById('current-match').innerText = 'Match ' + data.latest_over.match_index + ': ' + data.latest_over.hero_team + ' vs ' + data.latest_over.opponent_team;
                document.getElementById('current-phase').innerText = data.latest_over.phase;
                document.getElementById('current-over').innerText = data.latest_over.over_index;
            }

            if (data.metrics) {
                let html = '';
                for (const [model, stats] of Object.entries(data.metrics)) {
                    html += `<tr>
                        <td>${model}</td>
                        <td>${stats.next_match_accuracy_pct}%</td>
                        <td>${stats.final_winner_accuracy_pct}%</td>
                        <td>${stats.mean_brier_score}</td>
                    </tr>`;
                }
                document.getElementById('metrics-body').innerHTML = html;
            }

            if (data.predictions && data.predictions.length > 0) {
                let phtml = '<ul style="padding-left:20px;">';
                for (const p of data.predictions) {
                    phtml += `<li><strong>${p.desk_name}</strong> (${p.prediction_type}): ${p.predicted_team} — ${p.confidence_pct}%</li>`;
                }
                phtml += '</ul>';
                document.getElementById('predictions-container').innerHTML = phtml;
            }
        } catch (e) {
            console.error('Update error', e);
        }
    }
    setInterval(updateDashboard, 2000);
    updateDashboard();
</script>

</body>
</html>
"""


def parse_log_file(log_path: Path) -> Dict[str, Any]:
    """Read latest events and telemetry from JSONL log."""
    if not log_path.exists():
        return {"latest_over": None, "metrics": {}, "predictions": []}

    overs = []
    predictions = []
    metrics = {}

    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                evt_type = data.get("event_type")
                if evt_type == "OVER_EVENT":
                    overs.append(data)
                    if data.get("predictions"):
                        predictions.extend(data["predictions"])
                elif evt_type == "CAMPAIGN_SUMMARY":
                    metrics = data.get("metrics_per_model", {})
            except Exception:
                continue

    latest_over = overs[-1] if overs else None
    return {
        "latest_over": latest_over,
        "metrics": metrics,
        "predictions": predictions[-6:],
    }


class DashboardHandler(http.server.BaseHTTPRequestHandler):
    log_path = Path("logs/la28_cricket_benchmark.jsonl")

    def do_GET(self) -> None:
        if self.path == "/api/data":
            data = parse_log_file(self.log_path)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:
        return  # Suppress stdout HTTP server logging


def run_dashboard_server(port: int = 8080, log_path: str = "logs/la28_cricket_benchmark.jsonl") -> None:
    DashboardHandler.log_path = Path(log_path)
    with socketserver.TCPServer(("", port), DashboardHandler) as httpd:
        print(f"LA28 Cricket Dashboard running at http://localhost:{port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nDashboard server stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--log-path", default="logs/la28_cricket_benchmark.jsonl")
    args = parser.parse_args()
    run_dashboard_server(port=args.port, log_path=args.log_path)
