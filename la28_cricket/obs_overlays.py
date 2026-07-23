"""OBS Overlays for LA28 Cricket Benchmark."""
from __future__ import annotations
import http.server
import socketserver
import argparse
import sys

# Common HTML wrapper
def make_html(title: str, custom_css: str, body: str, custom_js: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Playfair+Display:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
    <style>
        :root {{
            --gold: #f59e0b;
            --red: #ef4444;
            --green: #10b981;
            --amber: #f59e0b;
            --dark: rgba(15, 23, 42, 0.85);
            --darker: rgba(2, 6, 23, 0.95);
            --text: #f8fafc;
        }}
        body {{
            margin: 0;
            overflow: hidden;
            font-family: 'Inter', sans-serif;
            color: var(--text);
            background: transparent;
        }}
        {custom_css}
    </style>
</head>
<body>
    {body}
    <script>
        const API_URL = window.location.port === '8081' ? 'http://localhost:8080/api/data' : '/api/data';
        {custom_js}
    </script>
</body>
</html>"""

SCOREBOARD_CSS = """
.scoreboard {
    position: absolute; top: 50px; left: 50px;
    background: var(--darker); border: 2px solid var(--gold); border-radius: 12px;
    padding: 15px 25px; display: flex; flex-direction: column; gap: 10px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.5); width: 300px;
}
.header { font-size: 14px; color: var(--gold); text-transform: uppercase; font-weight: bold; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 5px; }
.teams { display: flex; justify-content: space-between; align-items: center; font-size: 24px; font-weight: 700; }
.score { font-size: 36px; color: var(--gold); text-align: center; text-shadow: 0 0 10px rgba(245, 158, 11, 0.5); transition: transform 0.3s; }
.score.flip { transform: scale(1.1) rotateX(360deg); transition: transform 0.5s; }
.overs-container { display: flex; flex-direction: column; align-items: center; gap: 5px; font-size: 14px; color: #cbd5e1; }
.dots { display: flex; gap: 4px; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: #475569; }
.dot.filled { background: var(--gold); box-shadow: 0 0 5px var(--gold); }
"""

SCOREBOARD_JS = """
let lastScore = "";
async function update() {
    try {
        const res = await fetch(API_URL);
        const data = await res.json();
        if (data.latest_over) {
            const state = data.latest_over.state_after;
            const scoreStr = `${state.runs}/${state.wickets}`;
            document.getElementById('phase').textContent = data.latest_over.phase;
            document.getElementById('team1').textContent = getFlag(data.latest_over.hero_team);
            document.getElementById('team2').textContent = getFlag(data.latest_over.opponent_team);
            
            const scoreEl = document.getElementById('score');
            if (lastScore !== scoreStr && lastScore !== "") {
                scoreEl.classList.remove('flip');
                void scoreEl.offsetWidth;
                scoreEl.classList.add('flip');
            }
            scoreEl.textContent = scoreStr;
            lastScore = scoreStr;

            document.getElementById('over-text').textContent = `Over ${data.latest_over.over_index}/20`;
            const dots = document.getElementById('dots');
            dots.innerHTML = '';
            const balls = state.balls % 6;
            for(let i=0; i<6; i++) {
                dots.innerHTML += `<div class="dot ${i < balls ? 'filled' : ''}"></div>`;
            }
        }
    } catch (e) {}
}
function getFlag(team) {
    const flags = {'South Africa':'🇿🇦','Australia':'🇦🇺','India':'🇮🇳','Great Britain (via England)':'🇬🇧'};
    return flags[team] || '🏳️';
}
setInterval(update, 2000);
update();
"""

TICKER_CSS = """
.ticker-wrap { position: absolute; bottom: 0; width: 100%; background: var(--darker); height: 50px; border-top: 2px solid var(--gold); display: flex; align-items: center; overflow: hidden; }
.ticker-title { background: var(--gold); color: #000; font-weight: bold; height: 100%; padding: 0 20px; display: flex; align-items: center; z-index: 10; text-transform: uppercase; white-space: nowrap; }
.ticker-title.breaking { background: var(--red); color: white; animation: pulse 1s infinite; }
.ticker-content { display: flex; white-space: nowrap; padding-left: 100%; animation: ticker 25s linear infinite; }
.ticker-item { margin-right: 50px; font-size: 18px; display: inline-block; }
@keyframes ticker { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }
@keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.8; } 100% { opacity: 1; } }
"""

TICKER_JS = """
async function update() {
    try {
        const res = await fetch(API_URL);
        const data = await res.json();
        let items = [];
        if (data.latest_over) items.push(`Latest: ${data.latest_over.hero_team} vs ${data.latest_over.opponent_team} - ${data.latest_over.state_after.runs}/${data.latest_over.state_after.wickets}`);
        if (data.alerts && data.alerts.length > 0) {
            items.push(`🚨 ${data.alerts[0].text}`);
            document.getElementById('title').classList.add('breaking');
            document.getElementById('title').textContent = 'BREAKING';
        } else {
            document.getElementById('title').classList.remove('breaking');
            document.getElementById('title').textContent = 'LIVE';
        }
        if (data.predictions && data.predictions.length > 0) {
            const p = data.predictions[data.predictions.length - 1];
            items.push(`Prediction: ${p.desk_name} says ${p.predicted_team} (${p.confidence_pct}%)`);
        }
        document.getElementById('content').innerHTML = items.map(i => `<div class="ticker-item">${i}</div>`).join(' • ');
    } catch(e) {}
}
setInterval(update, 5000);
update();
"""

PREDICTIONS_CSS = """
.container { position: absolute; bottom: 80px; right: 50px; display: flex; gap: 20px; }
.desk { background: var(--dark); border: 1px solid rgba(255,255,255,0.2); border-radius: 12px; padding: 20px; width: 250px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); position: relative; }
.desk h3 { margin: 0 0 15px 0; font-size: 16px; color: #94a3b8; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 5px; }
.pred-row { margin-bottom: 10px; }
.pred-label { font-size: 12px; text-transform: uppercase; color: #94a3b8; margin-bottom: 5px; }
.pred-team { font-size: 18px; font-weight: bold; margin-bottom: 5px; }
.bar-bg { background: rgba(255,255,255,0.1); height: 8px; border-radius: 4px; overflow: hidden; }
.bar-fill { height: 100%; transition: width 1s ease-in-out, background-color 1s; }
.desk.leading { border-color: var(--gold); box-shadow: 0 0 20px rgba(245, 158, 11, 0.3); }
"""

PREDICTIONS_JS = """
function getColor(conf) { return conf > 75 ? 'var(--green)' : conf > 50 ? 'var(--amber)' : 'var(--red)'; }
async function update() {
    try {
        const res = await fetch(API_URL);
        const data = await res.json();
        if(data.predictions) {
            const desks = {};
            data.predictions.forEach(p => desks[p.desk_name] = p);
            
            let html = '';
            for (let [name, p] of Object.entries(desks)) {
                html += `
                <div class="desk">
                    <h3>${name}</h3>
                    <div class="pred-row">
                        <div class="pred-label">Match Winner</div>
                        <div class="pred-team">${p.predicted_team} (${p.confidence_pct}%)</div>
                        <div class="bar-bg">
                            <div class="bar-fill" style="width: ${p.confidence_pct}%; background: ${getColor(p.confidence_pct)}"></div>
                        </div>
                    </div>
                </div>`;
            }
            document.getElementById('container').innerHTML = html;
        }
    } catch(e) {}
}
setInterval(update, 3000);
update();
"""

COMMENTARY_CSS = """
.comm-box { position: absolute; bottom: 80px; left: 50px; background: var(--dark); border-left: 4px solid var(--gold); padding: 20px 30px; width: 600px; border-radius: 0 12px 12px 0; }
.comm-header { font-size: 12px; color: var(--gold); text-transform: uppercase; font-weight: bold; margin-bottom: 10px; display: flex; justify-content: space-between; }
.comm-text { font-family: 'Playfair Display', serif; font-size: 22px; line-height: 1.4; color: #f8fafc; }
.typewriter { overflow: hidden; border-right: .15em solid var(--gold); white-space: normal; animation: typing 3s steps(40, end), blink-caret .75s step-end infinite; }
@keyframes typing { from { width: 0; opacity: 0; } to { width: 100%; opacity: 1; } }
@keyframes blink-caret { from, to { border-color: transparent } 50% { border-color: var(--gold); } }
.fade-in { animation: fadeIn 0.5s ease-in; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
"""

COMMENTARY_JS = """
let lastOver = -1;
async function update() {
    try {
        const res = await fetch(API_URL);
        const data = await res.json();
        if (data.latest_over && data.latest_over.over_index !== lastOver) {
            lastOver = data.latest_over.over_index;
            document.getElementById('model').textContent = `Winning Comm: ${data.latest_over.winner_model}`;
            const textEl = document.getElementById('text');
            textEl.classList.remove('typewriter', 'fade-in');
            void textEl.offsetWidth;
            // Get text from judge verdict or just mock a snippet since we don't have full raw text in latest_over directly
            // Wait, data.latest_over has 'judge_verdict' and predictions have raw_text. But commentary feed is in data.commentary_feed
            let text = "What a fantastic over! The tension is palpable in the stadium.";
            if (data.commentary_feed && data.commentary_feed.length > 0) {
                text = data.commentary_feed[0].text;
            }
            textEl.textContent = text;
            textEl.classList.add('typewriter');
        }
    } catch(e) {}
}
setInterval(update, 2000);
update();
"""

ALERTS_CSS = """
.alert-container { position: absolute; top: 100px; left: 50%; transform: translateX(-50%); width: 600px; pointer-events: none; }
.alert { background: linear-gradient(135deg, #7f1d1d, #991b1b); border: 2px solid var(--gold); border-radius: 8px; padding: 20px; text-align: center; box-shadow: 0 10px 30px rgba(220, 38, 38, 0.4); transform: translateY(-150%); transition: transform 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275), opacity 0.5s; opacity: 0; }
.alert.show { transform: translateY(0); opacity: 1; }
.alert-title { color: var(--gold); font-size: 18px; font-weight: bold; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 10px; animation: flash 1s infinite; }
.alert-text { font-size: 24px; font-weight: 600; color: white; }
@keyframes flash { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
"""

ALERTS_JS = """
let showing = false;
let lastAlert = null;
async function update() {
    try {
        const res = await fetch(API_URL);
        const data = await res.json();
        if (data.alerts && data.alerts.length > 0 && !showing) {
            const alert = data.alerts[0];
            if (lastAlert === alert.timestamp) return;
            lastAlert = alert.timestamp;
            showing = true;
            
            document.getElementById('text').textContent = alert.text;
            const el = document.getElementById('alert');
            el.classList.add('show');
            
            setTimeout(() => {
                el.classList.remove('show');
                setTimeout(() => showing = false, 500);
            }, 8000);
        }
    } catch(e) {}
}
setInterval(update, 2000);
update();
"""

LEADERBOARD_CSS = """
.board { position: absolute; top: 50px; right: 50px; background: var(--darker); border: 1px solid var(--gold); border-radius: 12px; padding: 20px; width: 400px; box-shadow: 0 10px 30px rgba(0,0,0,0.6); }
.board-title { text-align: center; color: var(--gold); font-size: 20px; font-weight: bold; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 1px; }
.model-row { display: flex; align-items: center; margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.1); }
.model-row:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
.rank { font-size: 24px; font-weight: bold; color: var(--gold); width: 40px; }
.info { flex-grow: 1; }
.name { font-size: 16px; font-weight: 600; margin-bottom: 5px; display: flex; justify-content: space-between; }
.stats { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; font-size: 12px; color: #94a3b8; }
.stat-val { color: white; font-weight: bold; }
"""

LEADERBOARD_JS = """
async function update() {
    try {
        const res = await fetch(API_URL);
        const data = await res.json();
        if (data.metrics) {
            let models = Object.entries(data.metrics).map(([name, stats]) => ({name, stats}));
            models.sort((a, b) => b.stats.next_match_accuracy_pct - a.stats.next_match_accuracy_pct);
            
            let html = '';
            models.forEach((m, i) => {
                let h2h = data.head_to_head ? (data.head_to_head[m.name] || 0) : 0;
                html += `
                <div class="model-row">
                    <div class="rank">${i===0 ? '🏆' : '#'+(i+1)}</div>
                    <div class="info">
                        <div class="name"><span>${m.name}</span> <span class="stat-val">${m.stats.next_match_accuracy_pct}% Acc</span></div>
                        <div class="stats">
                            <div>Final Acc: <span class="stat-val">${m.stats.final_winner_accuracy_pct}%</span></div>
                            <div>Brier: <span class="stat-val">${m.stats.mean_brier_score}</span></div>
                            <div>H2H Wins: <span class="stat-val">${h2h}</span></div>
                        </div>
                    </div>
                </div>`;
            });
            document.getElementById('list').innerHTML = html;
        }
    } catch(e) {}
}
setInterval(update, 3000);
update();
"""

TIMELINE_CSS = """
.timeline-box { position: absolute; top: 50px; left: 50%; transform: translateX(-50%); background: var(--dark); padding: 20px 40px; border-radius: 30px; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 10px 20px rgba(0,0,0,0.5); }
.timeline { display: flex; align-items: center; gap: 20px; }
.match { display: flex; flex-direction: column; align-items: center; position: relative; z-index: 2; }
.match-dot { width: 20px; height: 20px; border-radius: 50%; background: #334155; border: 3px solid #1e293b; display: flex; align-items: center; justify-content: center; transition: all 0.3s; }
.match.completed .match-dot { background: var(--gold); border-color: #fff; }
.match.current .match-dot { background: var(--green); border-color: #fff; box-shadow: 0 0 15px var(--green); animation: pulse-green 1.5s infinite; }
.match-label { font-size: 10px; color: #94a3b8; margin-top: 8px; text-transform: uppercase; white-space: nowrap; }
.line { position: absolute; top: 30px; left: 40px; right: 40px; height: 4px; background: #334155; z-index: 1; }
@keyframes pulse-green { 0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); } 70% { box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); } 100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); } }
"""

TIMELINE_JS = """
async function update() {
    try {
        const res = await fetch(API_URL);
        const data = await res.json();
        if (data.tournament_progress) {
            let html = '';
            data.tournament_progress.forEach(m => {
                let status = m.completed ? 'completed' : (m.is_current ? 'current' : '');
                html += `
                <div class="match ${status}">
                    <div class="match-dot">${m.completed ? '✓' : ''}</div>
                    <div class="match-label">M${m.match_index}</div>
                </div>`;
            });
            document.getElementById('timeline').innerHTML = html;
        }
    } catch(e) {}
}
setInterval(update, 3000);
update();
"""

OVERLAYS = {
    "/obs/scoreboard": make_html(
        "Scoreboard", SCOREBOARD_CSS,
        """<div class="scoreboard">
            <div class="header" id="phase">Match Phase</div>
            <div class="teams"><span id="team1"></span> <span id="score">0/0</span> <span id="team2"></span></div>
            <div class="overs-container">
                <div id="over-text">Over 0/20</div>
                <div class="dots" id="dots"></div>
            </div>
        </div>""", SCOREBOARD_JS
    ),
    "/obs/ticker": make_html(
        "Ticker", TICKER_CSS,
        """<div class="ticker-wrap">
            <div class="ticker-title" id="title">LIVE</div>
            <div class="ticker-content" id="content"></div>
        </div>""", TICKER_JS
    ),
    "/obs/predictions": make_html(
        "Predictions", PREDICTIONS_CSS,
        """<div class="container" id="container"></div>""", PREDICTIONS_JS
    ),
    "/obs/commentary": make_html(
        "Commentary", COMMENTARY_CSS,
        """<div class="comm-box">
            <div class="comm-header">
                <span>LIVE COMMENTARY</span>
                <span id="model"></span>
            </div>
            <div class="comm-text" id="text"></div>
        </div>""", COMMENTARY_JS
    ),
    "/obs/alerts": make_html(
        "Alerts", ALERTS_CSS,
        """<div class="alert-container">
            <div class="alert" id="alert">
                <div class="alert-title">🚨 BREAKING EVENT 🚨</div>
                <div class="alert-text" id="text"></div>
            </div>
        </div>""", ALERTS_JS
    ),
    "/obs/leaderboard": make_html(
        "Leaderboard", LEADERBOARD_CSS,
        """<div class="board">
            <div class="board-title">Model Leaderboard</div>
            <div id="list"></div>
        </div>""", LEADERBOARD_JS
    ),
    "/obs/timeline": make_html(
        "Timeline", TIMELINE_CSS,
        """<div class="timeline-box">
            <div class="line"></div>
            <div class="timeline" id="timeline"></div>
        </div>""", TIMELINE_JS
    )
}

class OBSHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in OVERLAYS:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(OVERLAYS[self.path].encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8081)
    args = parser.parse_args()
    
    with socketserver.TCPServer(("", args.port), OBSHandler) as httpd:
        print(f"OBS Overlays serving at http://localhost:{args.port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Shutting down.")
            sys.exit(0)
