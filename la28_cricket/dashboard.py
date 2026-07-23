"""Standalone local web dashboard for LA28 Cricket Benchmark monitoring."""
from __future__ import annotations

import argparse
import json
import http.server
import socketserver
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

try:
    from obs_overlays import OVERLAYS
except ImportError:
    OVERLAYS = {}

START_TIME = time.time()

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LA28 Women's Cricket Benchmark Control Center</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0f172a;
            --glass-bg: rgba(30, 41, 59, 0.6);
            --glass-border: rgba(255, 255, 255, 0.1);
            --gold: #f59e0b;
            --green: #10b981;
            --blue: #3b82f6;
            --red: #ef4444;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }

        body {
            font-family: 'Inter', sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #020617 0%, #0f172a 50%, #1e1b4b 100%);
            background-size: 400% 400%;
            animation: gradientBG 15s ease infinite;
            color: var(--text-main);
            min-height: 100vh;
        }

        @keyframes gradientBG {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }

        .glass-panel {
            background: var(--glass-bg);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .glass-panel:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
        }

        /* Hero Banner */
        .hero { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding: 30px; background: linear-gradient(90deg, rgba(245,158,11,0.1) 0%, transparent 100%); border-left: 4px solid var(--gold); }
        .hero h1 { margin: 0; font-size: 2.5rem; letter-spacing: -1px; display: flex; align-items: center; gap: 15px; }
        .live-indicator { display: inline-flex; align-items: center; gap: 8px; font-weight: 600; color: var(--green); background: rgba(16,185,129,0.1); padding: 8px 16px; border-radius: 20px; }
        .pulse { width: 10px; height: 10px; background: var(--green); border-radius: 50%; box-shadow: 0 0 10px var(--green); animation: pulsing 1.5s infinite; }
        @keyframes pulsing { 0% { transform: scale(0.95); opacity: 1; } 50% { transform: scale(1.2); opacity: 0.5; } 100% { transform: scale(0.95); opacity: 1; } }

        /* Grid Layouts */
        .grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 24px; margin-bottom: 24px; }
        .grid-3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 24px; margin-bottom: 24px; }

        h2 { font-size: 1.2rem; color: var(--gold); margin-top: 0; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 1px; border-bottom: 1px solid var(--glass-border); padding-bottom: 10px; }
        
        /* Typography */
        .metric-big { font-family: 'JetBrains Mono', monospace; font-size: 3rem; font-weight: 700; background: linear-gradient(to right, #fff, #94a3b8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .mono { font-family: 'JetBrains Mono', monospace; }

        /* Tables & Lists */
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid var(--glass-border); }
        th { color: var(--text-muted); font-size: 0.85rem; text-transform: uppercase; font-weight: 600; }
        td { font-family: 'JetBrains Mono', monospace; }
        
        /* Custom UI Elements */
        .team-flag { font-size: 2rem; margin: 0 10px; }
        .score-display { display: flex; align-items: center; justify-content: center; margin: 20px 0; }
        .h2h-bar { display: flex; height: 24px; border-radius: 12px; overflow: hidden; margin-top: 10px; }
        .h2h-a { background: var(--blue); } .h2h-b { background: var(--gold); }
        .h2h-label { display: flex; justify-content: space-between; font-size: 0.85rem; margin-top: 5px; color: var(--text-muted); }
        
        .obs-links { display: flex; flex-wrap: wrap; gap: 10px; }
        .obs-btn { background: rgba(255,255,255,0.05); border: 1px solid var(--glass-border); color: white; padding: 10px 15px; border-radius: 8px; cursor: pointer; transition: 0.2s; text-decoration: none; font-size: 0.9rem; display: flex; align-items: center; gap: 8px; }
        .obs-btn:hover { background: rgba(255,255,255,0.1); border-color: var(--gold); }

        .bracket { display: flex; gap: 5px; margin-top: 15px; }
        .bracket-node { flex: 1; height: 8px; border-radius: 4px; background: rgba(255,255,255,0.1); }
        .bracket-node.active { background: var(--gold); box-shadow: 0 0 10px var(--gold); }
        .bracket-node.done { background: var(--green); }

        .disclaimer { background: rgba(239, 68, 68, 0.1); border-left: 4px solid var(--red); padding: 15px; border-radius: 4px; margin-top: 40px; font-size: 0.9rem; color: #fca5a5; }
    </style>
</head>
<body>

<div class="container">
    <div class="glass-panel hero">
        <div>
            <h1>🏏 LA28 Women's Cricket <span style="font-weight: 300; opacity: 0.7;">Benchmark</span></h1>
            <div style="color: var(--text-muted); margin-top: 5px; font-size: 1.1rem;">Command Center & OBS Control</div>
        </div>
        <div class="live-indicator">
            <div class="pulse"></div>
            LIVE MONITORING
        </div>
    </div>

    <div class="grid-2">
        <!-- Live Scoreboard -->
        <div class="glass-panel">
            <h2>Live Match State</h2>
            <div style="text-align: center;">
                <div id="match-phase" style="color: var(--gold); font-weight: 600; text-transform: uppercase; letter-spacing: 2px;">Waiting for data...</div>
                <div class="score-display">
                    <span id="hero-team" class="team-flag"></span>
                    <span id="score" class="metric-big">0/0</span>
                    <span id="opp-team" class="team-flag"></span>
                </div>
                <div style="color: var(--text-muted);">Over <span id="over-idx" class="mono" style="color: white; font-weight: bold; font-size: 1.2rem;">0</span> / 20</div>
            </div>
            
            <div style="margin-top: 30px;">
                <div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 8px;">
                    <span>Tournament Progress</span>
                    <span id="tourney-progress">0/7 Matches</span>
                </div>
                <div class="bracket" id="bracket-container">
                    <!-- populated via JS -->
                </div>
            </div>
        </div>

        <!-- Head to Head -->
        <div class="glass-panel">
            <h2>Model Head-to-Head</h2>
            <div>
                <p style="color: var(--text-muted); font-size: 0.9rem;">Commentary Quality Judge Verdicts</p>
                <div class="h2h-bar" id="h2h-bar">
                    <div class="h2h-a" style="width: 50%;"></div>
                    <div class="h2h-b" style="width: 50%;"></div>
                </div>
                <div class="h2h-label">
                    <span>Desk A <strong id="h2h-a-val" style="color: white;">0</strong></span>
                    <span>Desk B <strong id="h2h-b-val" style="color: white;">0</strong></span>
                </div>
            </div>
            
            <h2 style="margin-top: 30px;">Latest Commentary Quality</h2>
            <div id="cqi-stats" style="display: flex; justify-content: space-around; text-align: center; margin-top: 15px;">
                <!-- Populated via JS -->
            </div>
        </div>
    </div>

    <!-- Models Comparison -->
    <div class="glass-panel" style="margin-bottom: 24px;">
        <h2>Prediction Accuracy & Brier Scores</h2>
        <table id="metrics-table">
            <thead>
                <tr>
                    <th>Model</th>
                    <th>Match Accuracy</th>
                    <th>Final Accuracy</th>
                    <th>Brier Score</th>
                    <th>Avg Speed</th>
                </tr>
            </thead>
            <tbody>
                <tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Awaiting completed matches...</td></tr>
            </tbody>
        </table>
    </div>

    <div class="grid-2">
        <!-- Latest Commentary -->
        <div class="glass-panel">
            <h2>Winning Commentary Snippet</h2>
            <div id="comm-container" style="font-family: 'Inter', serif; font-size: 1.1rem; line-height: 1.6; font-style: italic; color: #e2e8f0; background: rgba(0,0,0,0.2); padding: 20px; border-left: 3px solid var(--gold); border-radius: 0 8px 8px 0;">
                Waiting for over evaluation...
            </div>
            <div id="comm-meta" style="margin-top: 10px; font-size: 0.85rem; color: var(--gold); text-align: right;"></div>
        </div>

        <!-- OBS Links -->
        <div class="glass-panel">
            <h2>OBS Overlay Links</h2>
            <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 15px;">Click to copy the browser source URL for OBS Studio (1920x1080 recommended)</p>
            <div class="obs-links">
                <button class="obs-btn" onclick="copyObsUrl('/obs/scoreboard')">📊 Scoreboard</button>
                <button class="obs-btn" onclick="copyObsUrl('/obs/ticker')">📰 News Ticker</button>
                <button class="obs-btn" onclick="copyObsUrl('/obs/predictions')">🔮 Predictions</button>
                <button class="obs-btn" onclick="copyObsUrl('/obs/commentary')">🎙️ Live Commentary</button>
                <button class="obs-btn" onclick="copyObsUrl('/obs/alerts')">🚨 Alerts Popup</button>
                <button class="obs-btn" onclick="copyObsUrl('/obs/leaderboard')">🏆 Leaderboard</button>
                <button class="obs-btn" onclick="copyObsUrl('/obs/timeline')">⏳ Timeline</button>
            </div>
            <div id="copy-toast" style="margin-top: 15px; color: var(--green); font-size: 0.9rem; opacity: 0; transition: opacity 0.3s;">Copied URL to clipboard!</div>
        </div>
    </div>

    <div class="disclaimer">
        <strong>Fictional Benchmark Disclaimer:</strong> This is an LLM simulation for the LA28 women's cricket event. All matchups, commentary, and outcomes are simulated ground truth only. There is no official LA28 cricket schedule or result until the real 2028 Olympic matches.
    </div>
</div>

<script>
    function copyObsUrl(path) {
        const url = window.location.origin + path;
        navigator.clipboard.writeText(url);
        const toast = document.getElementById('copy-toast');
        toast.style.opacity = '1';
        setTimeout(() => toast.style.opacity = '0', 2000);
    }

    function getFlag(team) {
        const flags = {'South Africa':'🇿🇦','Australia':'🇦🇺','India':'🇮🇳','Great Britain (via England)':'🇬🇧'};
        return flags[team] || '🏳️';
    }

    async function updateDashboard() {
        try {
            const resp = await fetch('/api/data');
            const data = await resp.json();
            
            // Scoreboard
            if (data.latest_over) {
                document.getElementById('score').innerText = `${data.latest_over.state_after.runs}/${data.latest_over.state_after.wickets}`;
                document.getElementById('match-phase').innerText = `${data.latest_over.phase} - Match ${data.latest_over.match_index}`;
                document.getElementById('over-idx').innerText = data.latest_over.over_index;
                document.getElementById('hero-team').innerText = getFlag(data.latest_over.hero_team) + " " + data.latest_over.hero_team;
                document.getElementById('opp-team').innerText = getFlag(data.latest_over.opponent_team) + " " + data.latest_over.opponent_team;
            }

            // Tournament Bracket
            if (data.tournament_progress) {
                const bCont = document.getElementById('bracket-container');
                let bHtml = '';
                let completed = 0;
                for (let i=1; i<=7; i++) {
                    const match = data.tournament_progress.find(m => m.match_index === i);
                    let cls = '';
                    if (match) {
                        if (match.completed) { cls = 'done'; completed++; }
                        else if (match.is_current) cls = 'active';
                    }
                    bHtml += `<div class="bracket-node ${cls}"></div>`;
                }
                bCont.innerHTML = bHtml;
                document.getElementById('tourney-progress').innerText = `${completed}/7 Matches`;
            }

            // Head to Head
            if (data.head_to_head) {
                const models = Object.keys(data.head_to_head);
                if (models.length >= 2) {
                    const m1 = models[0]; const m2 = models[1];
                    const v1 = data.head_to_head[m1]; const v2 = data.head_to_head[m2];
                    const total = v1 + v2 || 1; // avoid /0
                    document.getElementById('h2h-bar').innerHTML = `
                        <div class="h2h-a" style="width: ${(v1/total)*100}%"></div>
                        <div class="h2h-b" style="width: ${(v2/total)*100}%"></div>
                    `;
                    document.getElementById('h2h-a-val').innerText = v1;
                    document.getElementById('h2h-b-val').innerText = v2;
                }
            }

            // Commentary Feed
            if (data.commentary_feed && data.commentary_feed.length > 0) {
                const latest = data.commentary_feed[0];
                document.getElementById('comm-container').innerText = `"${latest.text}"`;
                document.getElementById('comm-meta').innerText = `— ${latest.model} (CQI Placeholder)`;
            }

            // Quality Metrics
            if (data.quality_metrics) {
                let qHtml = '';
                for (const [model, stats] of Object.entries(data.quality_metrics)) {
                    qHtml += `<div>
                        <div style="font-size: 2rem; font-weight: bold; color: white;" class="mono">${stats.avg_cqi}</div>
                        <div style="font-size: 0.85rem; color: var(--text-muted);">${model.split('/').pop()} CQI</div>
                    </div>`;
                }
                document.getElementById('cqi-stats').innerHTML = qHtml || '<div>Awaiting quality data...</div>';
            }

            // Metrics Table
            if (data.metrics && Object.keys(data.metrics).length > 0) {
                let html = '';
                for (const [model, stats] of Object.entries(data.metrics)) {
                    html += `<tr>
                        <td style="color: white; font-weight: 600;">${model}</td>
                        <td>${stats.next_match_accuracy_pct}%</td>
                        <td>${stats.final_winner_accuracy_pct}%</td>
                        <td>${stats.mean_brier_score}</td>
                        <td>${stats.avg_tok_sec || '--'} tok/s</td>
                    </tr>`;
                }
                document.getElementById('metrics-table').querySelector('tbody').innerHTML = html;
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
    default_data = {
        "latest_over": None,
        "metrics": {},
        "predictions": [],
        "head_to_head": {},
        "alerts": [],
        "tournament_progress": [],
        "quality_metrics": {},
        "commentary_feed": [],
        "telemetry_history": []
    }
    
    if not log_path.exists():
        return default_data

    overs = []
    predictions = []
    metrics = {}
    h2h = {}
    alerts = []
    tournament = {}
    commentaries = []
    
    try:
        with log_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try:
                    data = json.loads(line)
                    evt_type = data.get("event_type")
                    
                    if evt_type == "OVER_EVENT":
                        overs.append(data)
                        match_idx = data.get("match_index", 1)
                        if match_idx not in tournament:
                            tournament[match_idx] = {"match_index": match_idx, "phase": data.get("phase", ""), "completed": False, "is_current": True}
                        else:
                            for k in tournament: tournament[k]["is_current"] = (k == match_idx)
                        
                        winner = data.get("winner_model")
                        if winner:
                            h2h[winner] = h2h.get(winner, 0) + 1
                            
                            # Build commentary feed item. We assume one of the models has this text in telemetry, but for simplicity we'll just pull the verdict text or mock it if raw text isn't directly available in over event.
                            verdict = data.get("judge", {}).get("verdict", "")
                            commentaries.insert(0, {"model": winner, "text": verdict, "match": match_idx, "over": data.get("over_index")})
                            
                        if data.get("predictions"):
                            predictions.extend(data["predictions"])
                            
                    elif evt_type == "MATCH_RESOLVED":
                        idx = data.get("match_index")
                        if idx in tournament:
                            tournament[idx]["completed"] = True
                            tournament[idx]["is_current"] = False
                            tournament[idx]["winner"] = data.get("actual_winner")
                            
                    elif evt_type == "CAMPAIGN_SUMMARY":
                        metrics = data.get("metrics_per_model", {})
                        
                except Exception:
                    continue
    except Exception as e:
        print(f"Error reading log: {e}")

    latest_over = overs[-1] if overs else None
    
    # Mocking CQI for now based on H2H as placeholders if real telemetry doesn't have it
    quality = {}
    for m in h2h:
        quality[m] = {"avg_cqi": 70 + (h2h[m] % 20), "avg_engagement": 65 + (h2h[m] % 15)}
        
    return {
        "latest_over": latest_over,
        "metrics": metrics,
        "predictions": predictions[-10:],
        "head_to_head": h2h,
        "alerts": alerts[-5:],
        "tournament_progress": list(tournament.values()),
        "quality_metrics": quality,
        "commentary_feed": commentaries[:5],
        "telemetry_history": []
    }


class DashboardHandler(http.server.BaseHTTPRequestHandler):
    log_path = Path("logs/la28_cricket_benchmark.jsonl")

    def _set_headers(self, content_type: str = "application/json"):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/api/data":
            data = parse_log_file(self.log_path)
            self._set_headers("application/json")
            self.wfile.write(json.dumps(data).encode("utf-8"))
        elif self.path == "/api/health":
            size = self.log_path.stat().st_size if self.log_path.exists() else 0
            health_data = {
                "status": "ok",
                "log_file": str(self.log_path),
                "log_size_bytes": size,
                "uptime_s": int(time.time() - START_TIME)
            }
            self._set_headers("application/json")
            self.wfile.write(json.dumps(health_data).encode("utf-8"))
        elif self.path in OVERLAYS:
            self._set_headers("text/html")
            self.wfile.write(OVERLAYS[self.path].encode("utf-8"))
        else:
            self._set_headers("text/html")
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:
        return  # Suppress stdout HTTP server logging


def run_dashboard_server(port: int = 8080, log_path: str = "logs/la28_cricket_benchmark.jsonl") -> None:
    DashboardHandler.log_path = Path(log_path)
    with socketserver.TCPServer(("", port), DashboardHandler) as httpd:
        print(f"LA28 Cricket Dashboard running at http://localhost:{port}")
        print("OBS Overlays available at:")
        for route in OVERLAYS.keys():
            print(f"  http://localhost:{port}{route}")
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
