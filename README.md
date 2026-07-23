# LA28 Women's Cricket LLM Benchmark

[![Benchmark Status](https://img.shields.io/badge/LA28--Cricket--Benchmark-Standalone-brightgreen)](#)
[![Compatibility](https://img.shields.io/badge/API-OpenAI--Compatible-blue)](#)
[![LLMs Supported](https://img.shields.io/badge/Models-Any--LLM-purple)](#)

## 📌 Crucial Disclaimers & Fair Usage

1. **Fictional Benchmark Only**: This repository hosts a **fictional LA28 women’s cricket LLM benchmark**. The tournament arc and match narrative are synthetic benchmark fixtures designed for evaluating language model performance.
2. **Simulated Ground Truth**: Current tournament results are **simulated ground truth only**.
3. **No Official LA28 Winner**: There is **no official LA28 cricket winner** until the real 2028 Olympic matches occur in Los Angeles.
4. **Future Scorecard Importable**: Future official 2028 scorecards can be imported into this repository (`la28-import-scorecard`) and evaluated against locked, immutable model predictions.
5. **Universal LLM & Hardware Compatibility**: This benchmark connects to **ANY OpenAI-compatible API endpoint** (`http://localhost:1234/v1`, Ollama, LM Studio, vLLM, LocalAI, Aphrodite, OpenAI API, etc.) running on **ANY hardware** (Mac, Windows, Linux, local GPUs, cloud instances, or CPUs).
6. **Independent Broadcast Desks**: Two independent broadcast desks/models are evaluated fairly:
   - **Desk A**: Configurable LLM (Default: `qwen/qwen2.5-coder-14b`) — *Southern Hemisphere Sports Network*
   - **Desk B**: Configurable LLM (Default: `qwen/qwen3-coder-30b`) — *Olympic Cricket Analysis Desk*
7. **Zero Model Leakage**: Desk A and Desk B predictions and commentary are generated in strict isolation. Neither desk can see or influence the other desk's prompt, outputs, or predictions.
8. **OBS is Optional**: OBS is an optional visual streaming adapter and is **not a core dependency**.
9. **Fictional Elements**: The fictional broadcast story arc may feature recurring surprises (e.g. a boundary couch, two ordinary men in sleepwear, a passing spaceship, or an intelligent two-headed spaceship character giving fielding advice). These creative narrative elements **never affect match scoring or outcome determination**.

---

## 🎯 Tournament Format & Bracket

The benchmark evaluates models across a **seven-match fictional tournament campaign** totaling **140 team overs** (20 overs per T20 match):

1. **Group Match 1**: South Africa `[ZA]` vs Australia `[AUS]`
2. **Group Match 2**: South Africa `[ZA]` vs Great Britain (via England) `[GB]`
3. **Group Match 3**: South Africa `[ZA]` vs India `[IND]`
4. **Group Match 4**: South Africa `[ZA]` vs Qualifier 5 `[Q5]`
5. **Group Match 5**: South Africa `[ZA]` vs Qualifier 6 `[Q6]`
6. **Semifinal**: South Africa `[ZA]` vs India `[IND]`
7. **Gold-Medal Final**: South Africa `[ZA]` vs Australia `[AUS]`

---

## 📐 Benchmark Dimensions

This framework evaluates models across multiple dimensions beyond standard log-likelihood:

- **Cricket Quality Index (CQI)**: Measures domain-specific fluency, accurate terminology usage, and logical adherence to T20 cricket mechanics.
- **Engagement Score**: A composite metric scoring the vividness of radio broadcast descriptions, crowd atmosphere synthesis, and pacing.
- **Prediction Stability**: Evaluates how consistently a model's live predictions align with its early-stage predictions, punishing erratic swings.
- **Hallucination Detection**: Penalizes non-existent rule inventions (e.g., a "12-run super ball") or hallucinated match actions outside the prompt's bounded constraints.
- **Head-to-Head Judgement**: An independent judge model (typically Model B or a separate robust model) evaluates A vs B on narrative and atmospheric delivery.

---

## ⚙️ Fixed Baseline & Sampling Parameters

To ensure strict fairness, repeatability, and non-misleading comparison, all model calls execute with a locked baseline prompt template (`v1.0`) and fixed sampling parameters:

```json
{
  "temperature": 0.2,
  "top_p": 0.9,
  "seed": 42,
  "presence_penalty": 0,
  "frequency_penalty": 0,
  "max_tokens": 300
}
```

Prior to running live benchmark calls, check your endpoint using `la28-verify-endpoint` to confirm exact active model IDs returned by your inference server.

---

## 🌍 Environment Variables

You can configure any endpoint, model ID, or hardware description via environment variables:

- `LA28_ENDPOINT`: Override the inference endpoint URL (default: `http://localhost:1234/v1`).
- `LA28_MODEL_A`: Set model ID for Desk A (default: `qwen/qwen2.5-coder-14b` or any active model ID).
- `LA28_MODEL_B`: Set model ID for Desk B (default: `qwen/qwen3-coder-30b` or any active model ID).
- `LA28_SERVER_HW`: Set custom inference server label (default: `OpenAI-Compatible Inference Server`).
- `LA28_CLIENT_HW`: Set custom client/dashboard label (default: `Benchmark Client Machine`).

---

## 📊 Recorded Benchmark Metrics

Every benchmark run emits structured JSONL audit logs (`logs/la28_cricket_benchmark.jsonl`) recording:

- **Prediction Accuracy (%)**: Next-match winner accuracy & campaign gold-medal winner accuracy.
- **Confidence Calibration (Brier Score)**: Mean Brier Score $BS = \frac{1}{N} \sum (c_i - y_i)^2$ evaluating model confidence vs actual outcomes.
- **Wall-Clock Latency (s)**: Individual call latency, total run latency, mean, and p95 latency.
- **Token Telemetry**: Total completion tokens, prompt tokens, and generation throughput (**tok/s**).
- **Error Tracking**: API connection errors, timeouts, or parse failures.

---

## 📁 Repository Structure

```
la28-cricket-benchmark/
├── README.md                          # Project documentation and disclaimers
├── pyproject.toml                     # Python package metadata (entry points)
├── requirements.txt                   # Dependency specifications
├── .gitignore                         # Ignore logs, caches, and build artifacts
├── la28_cricket/                      # Core python benchmark package
│   ├── __init__.py
│   ├── config.py                      # Baseline config, schedule, ground truth, constants
│   ├── models.py                      # HTTP client for remote endpoint & dry-run
│   ├── schema.py                      # Structured JSONL schema definitions & data models
│   ├── metrics.py                     # Accuracy, Brier score calibration, telemetry
│   ├── benchmark.py                   # 140-over campaign benchmark orchestrator
│   ├── dashboard.py                   # Standalone local web dashboard server
│   └── obs_overlays.py                # Broadcast overlay web server for OBS integration
├── scripts/                           # CLI tools (exposed via pyproject.toml)
│   ├── run_benchmark.py               # Main launcher (--dry-run, --overs, --endpoint)
│   ├── verify_remote_endpoint.py      # Health-check remote RTX 4060
│   └── import_official_scorecard.py   # Evaluate predictions against official scorecards
├── tests/                             # Automated test suite
│   ├── test_config.py                 # Schedule, surprises, environment variables
│   ├── test_isolation.py              # Zero-leakage desk prompt isolation
│   ├── test_schema_and_metrics.py     # Metrics & JSONL schema unit tests
│   ├── test_benchmark_dryrun.py       # Full dry-run campaign integration test
│   ├── test_cli_scripts.py            # CLI argument parsing and execution
│   └── test_obs_overlays.py           # OBS overlay route testing
│   └── fixtures/                      # Test assets (e.g. sample_scorecard.json)
└── logs/                              # Directory for output JSONL audit logs
```

---

## 💻 🖥️ Live Studio Broadcast & Stadium Visualizer App (`frontend/`)

A standalone Vite web application providing a **broadcast-grade visual experience** compatible with Mac, Windows, and Linux.

### Features
- **🏟️ 2D Stadium Canvas Engine**: Animated stadium under floodlights, shot trajectory arcs (sixes, fours, wickets), Hawk-Eye tracking mode, and fireworks display.
- **🔊 Web Audio Ambiance & SFX**: Synthesized bat-on-ball crack sound, crowd cheering roars, and stadium background ambiance (zero audio asset dependencies).
- **🎙️ Web Speech AI Voiceover**: Live commentary text-to-speech engine with distinct pitch/voice profiles for Desk A vs Desk B.
- **📺 OBS Producer Suite**: Quick access and one-click URL copying for all 7 broadcast overlays.
- **⚡ Dual Data Mode**: Automatically syncs with Python backend (`http://localhost:8080/api/data`) or falls back to an offline browser simulation.

### Running the Studio App

```bash
# 1. Navigate to frontend
cd frontend

# 2. Run local development server
npm run dev
# Open http://localhost:5173 in any browser (Mac / Windows / Linux)

# Or serve the production build directly via Python server at http://localhost:8080/studio
python la28_cricket/dashboard.py --port 8080
```

---

## 🛠️ Development Setup

To install the benchmark tools in editable mode with development dependencies:

```bash
pip install -e .[dev]
```

Run the complete automated test suite locally:
```bash
pytest tests/
```

---

## 📺 OBS Integration for Streamers

The benchmark includes a dedicated lightweight web server (`obs_overlays.py`) that serves transparent HTML pages designed to be captured by OBS Studio as **Browser Sources**. 

### Available Overlay URLs:
When running on port `8081` (default):
- **Scorebug**: `http://localhost:8081/scoreboard` — Live score, current over, and team graphics.
- **Predictions**: `http://localhost:8081/predictions` — Real-time model prediction confidences and Brier scores.
- **Commentary**: `http://localhost:8081/` — Live scrolling text from the winning broadcast desk.

### Setup Instructions in OBS:
1. Under "Sources", click the **+** button and select **Browser**.
2. Name it (e.g., "LA28 Scorebug").
3. Uncheck "Local file".
4. Enter the URL (e.g., `http://localhost:8081/scoreboard`).
5. **Recommended Dimensions**: 
   - Width: `1920`, Height: `1080` (The overlays are designed for 1080p canvases with transparent backgrounds).
6. Click **OK**.

---

## 🚀 Quick Start & Verification

### 1. Verify Remote Endpoint Health
Before starting a live run on the remote RTX 4060 server (`http://10.55.0.2:1234/v1`):

```bash
la28-verify-endpoint --endpoint http://10.55.0.2:1234/v1
```

### 2. Run a Benchmark Campaign (with OBS Overlays)
Execute a live benchmark campaign, enabling rich verbose output and auto-launching the OBS overlay server on port 8081:

```bash
la28-run-benchmark --verbose --obs-port 8081
```

To run a simulated 140-over dry-run campaign without calling remote network APIs:
```bash
la28-run-benchmark --dry-run --overs 140
```

### 3. Launch Live Web Dashboard
Launch the standalone local web monitoring interface:

```bash
python la28_cricket/dashboard.py --port 8080
```
Open `http://localhost:8080` in your web browser.

---

## 🔒 Auditability & Replayability

Each campaign run generates an immutable `run_id` with full provenance details embedded in the JSONL header (`RUN_START`). All prediction outputs (`NEXT_MATCH_PREDICTION` and `FINAL_PREDICTION`) recorded in over 1 are permanently locked and cannot be mutated or overwritten by subsequent overs.

When official 2028 Olympic cricket scorecards become available, evaluate locked predictions using:

```bash
la28-import-scorecard --log-path logs/la28_cricket_benchmark.jsonl --scorecard path/to/official_2028_scorecard.json
```
