/**
 * Data Manager & Standalone Demo Simulation Engine
 * Polling real Python backend or running an offline browser simulation.
 */
export class DataManager {
  constructor() {
    this.apiEndpoints = ['http://localhost:8080/api/data', 'http://localhost:8000/api/data'];
    this.activeEndpoint = null;
    this.isLiveBackend = false;
    this.onDataUpdateCallbacks = [];
    
    // Standalone Demo State
    this.demoState = {
      matchIndex: 1,
      overIndex: 1,
      runs: 0,
      wickets: 0,
      balls: 0,
      heroTeam: 'South Africa',
      opponentTeam: 'Australia',
      phase: 'Group match 1',
      modelAWins: 3,
      modelBWins: 2,
    };

    this.init();
  }

  onDataUpdate(cb) {
    this.onDataUpdateCallbacks.push(cb);
  }

  async init() {
    await this.checkBackend();
    this.startPolling();
  }

  async checkBackend() {
    for (const url of this.apiEndpoints) {
      try {
        const res = await fetch(url, { signal: AbortSignal.timeout(1500) });
        if (res.ok) {
          this.activeEndpoint = url;
          this.isLiveBackend = true;
          return true;
        }
      } catch (e) {
        // Backend offline
      }
    }
    this.isLiveBackend = false;
    return false;
  }

  startPolling() {
    setInterval(async () => {
      let data = null;
      if (this.isLiveBackend && this.activeEndpoint) {
        try {
          const res = await fetch(this.activeEndpoint);
          if (res.ok) {
            data = await res.json();
          }
        } catch (e) {
          this.isLiveBackend = false;
        }
      }

      if (!data) {
        // Fallback to Standalone Demo simulation step
        data = this.generateDemoStep();
      }

      this.onDataUpdateCallbacks.forEach(cb => cb(data, this.isLiveBackend));
    }, 2500);
  }

  generateDemoStep() {
    // Progress balls & overs
    this.demoState.balls += 6;
    this.demoState.overIndex += 1;

    const runsScored = Math.floor(Math.random() * 12) + 2;
    this.demoState.runs += runsScored;

    const isWicket = Math.random() < 0.15;
    if (isWicket && this.demoState.wickets < 10) {
      this.demoState.wickets += 1;
    }

    if (this.demoState.overIndex > 20) {
      this.demoState.overIndex = 1;
      this.demoState.matchIndex = (this.demoState.matchIndex % 7) + 1;
      this.demoState.runs = 0;
      this.demoState.wickets = 0;
      this.demoState.balls = 0;
      
      const opponents = ['Australia', 'Great Britain [GB]', 'India', 'Qualifier 5', 'Qualifier 6', 'India (Semi)', 'Australia (Final)'];
      this.demoState.opponentTeam = opponents[this.demoState.matchIndex - 1];
    }

    const winnerIsA = Math.random() > 0.45;
    if (winnerIsA) this.demoState.modelAWins += 1; else this.demoState.modelBWins += 1;

    const surprises = [
      "a mysterious coach appears at the boundary rope",
      "two ordinary-looking men in sleepwear sit on a couch near the commentary box",
      "a silent spaceship crosses the night sky above the stadium",
      "an intelligent two-headed spaceship character gives fielding tips"
    ];
    const triggerSurprise = (this.demoState.overIndex % 5 === 4);
    const surpriseText = triggerSurprise ? surprises[Math.floor(Math.random() * surprises.length)] : null;

    const cqiA = Math.floor(Math.random() * 20) + 75;
    const cqiB = Math.floor(Math.random() * 18) + 80;

    return {
      latest_over: {
        match_index: this.demoState.matchIndex,
        over_index: this.demoState.overIndex,
        hero_team: this.demoState.heroTeam,
        opponent_team: this.demoState.opponentTeam,
        phase: `Match ${this.demoState.matchIndex} of 7`,
        state_after: { runs: this.demoState.runs, wickets: this.demoState.wickets, balls: this.demoState.balls },
        winner_model: winnerIsA ? 'qwen/qwen2.5-coder-14b' : 'qwen/qwen3-coder-30b',
        judge_verdict: winnerIsA ? "WINNER: A\nSCORE: 9/10\nREASON: Superior radio drama." : "WINNER: B\nSCORE: 10/10\nREASON: Crisp boundary analysis.",
        surprise: surpriseText,
      },
      commentary_feed: [
        {
          desk_name: winnerIsA ? "Qwen2.5 — Southern Hemisphere Sports" : "Qwen3 — Olympic Analysis Desk",
          text: `Over ${this.demoState.overIndex}: South Africa builds relentless momentum! ${runsScored} runs scored off clean boundary driving under stadium lights!`,
          cqi: winnerIsA ? cqiA : cqiB,
          eng: Math.floor(Math.random() * 15) + 80,
          toks: (Math.random() * 10 + 38).toFixed(1)
        }
      ],
      metrics: {
        "qwen/qwen2.5-coder-14b": {
          next_match_accuracy_pct: 85.0,
          final_winner_accuracy_pct: 100.0,
          mean_brier_score: 0.035,
          avg_cqi_score: cqiA,
          avg_engagement_score: 83.5,
          tok_per_sec: 42.1
        },
        "qwen/qwen3-coder-30b": {
          next_match_accuracy_pct: 100.0,
          final_winner_accuracy_pct: 100.0,
          mean_brier_score: 0.024,
          avg_cqi_score: cqiB,
          avg_engagement_score: 88.2,
          tok_per_sec: 38.4
        }
      },
      head_to_head: {
        model_a_wins: this.demoState.modelAWins,
        model_b_wins: this.demoState.modelBWins
      },
      predictions: [
        { desk_name: "Desk A", prediction_type: "NEXT_MATCH", predicted_team: "South Africa", confidence_pct: 85.0 },
        { desk_name: "Desk B", prediction_type: "NEXT_MATCH", predicted_team: "South Africa", confidence_pct: 88.0 }
      ]
    };
  }
}
