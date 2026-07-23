/**
 * Polls the Python dashboard when present and otherwise runs a deterministic,
 * visibly labeled browser demonstration. Demo values never masquerade as
 * official 2028 results.
 */
export class DataManager {
  constructor() {
    this.apiEndpoints = ['http://localhost:8080/api/data', 'http://localhost:8000/api/data'];
    this.activeEndpoint = null;
    this.isLiveBackend = false;
    this.onDataUpdateCallbacks = [];
    this.seed = 280714;
    this.models = ['qwen/qwen2.5-coder-14b', 'qwen/qwen3-coder-30b'];
    this.opponents = [
      'Australia',
      'Great Britain (via England)',
      'India',
      'Qualifier 5',
      'Qualifier 6',
      'India',
      'Australia',
    ];
    this.phases = [
      'Group match 1',
      'Group match 2',
      'Group match 3',
      'Group match 4',
      'Group match 5',
      'Semifinal',
      'Gold medal final',
    ];
    this.demoState = {
      matchIndex: 1,
      overIndex: 3,
      runs: 27,
      wickets: 1,
      balls: 18,
      modelAWins: 2,
      modelBWins: 1,
      tick: 0,
    };
    this.init();
  }

  random() {
    this.seed = (this.seed * 1664525 + 1013904223) >>> 0;
    return this.seed / 4294967296;
  }

  onDataUpdate(callback) {
    this.onDataUpdateCallbacks.push(callback);
  }

  async init() {
    await this.checkBackend();
    await this.publishNext();
    window.setInterval(() => this.publishNext(), 2500);
  }

  async checkBackend() {
    for (const url of this.apiEndpoints) {
      try {
        const response = await fetch(url, { signal: AbortSignal.timeout(1200) });
        if (response.ok) {
          this.activeEndpoint = url;
          this.isLiveBackend = true;
          return;
        }
      } catch {
        // Continue to the next configured local dashboard.
      }
    }
    this.isLiveBackend = false;
  }

  async publishNext() {
    let data;
    if (this.isLiveBackend && this.activeEndpoint) {
      try {
        const response = await fetch(this.activeEndpoint);
        if (response.ok) data = await response.json();
      } catch {
        this.isLiveBackend = false;
      }
    }
    if (!data) data = this.generateDemoStep();
    this.onDataUpdateCallbacks.forEach((callback) => callback(data, this.isLiveBackend));
  }

  generateDemoStep() {
    const state = this.demoState;
    state.tick += 1;
    state.overIndex += 1;
    state.balls += 6;
    const runsScored = 3 + Math.floor(this.random() * 11);
    state.runs += runsScored;
    if (this.random() < 0.14 && state.wickets < 10) state.wickets += 1;

    if (state.overIndex > 20) {
      state.overIndex = 1;
      state.matchIndex = (state.matchIndex % 7) + 1;
      state.runs = 5 + Math.floor(this.random() * 8);
      state.wickets = 0;
      state.balls = 6;
    }

    const winnerIsA = state.tick % 3 === 0 || this.random() > 0.52;
    if (winnerIsA) state.modelAWins += 1;
    else state.modelBWins += 1;

    const opponent = this.opponents[state.matchIndex - 1];
    const phase = this.phases[state.matchIndex - 1];
    const surprises = [
      'A mysterious coach appears at the boundary rope.',
      'Two ordinary people in sleepwear settle onto the roaming boundary couch.',
      'A silent spacecraft crosses the San Gabriel skyline.',
      'A friendly two-headed visitor offers fielding geometry from the concourse.',
    ];
    const surprise = state.overIndex % 6 === 0
      ? surprises[(state.matchIndex + state.overIndex) % surprises.length]
      : null;

    const cqiA = 79 + Math.floor(this.random() * 14);
    const cqiB = 82 + Math.floor(this.random() * 13);
    const speedA = 36 + this.random() * 12;
    const speedB = 29 + this.random() * 10;
    const deskAText = `Over ${state.overIndex}: the field tightens, the Pomona crowd leans forward, and ${runsScored} runs arrive through precise placement.`;
    const deskBText = `The San Gabriels frame the shot as South Africa turns over ${state.overIndex} into ${runsScored} more runs and a rising wall of sound.`;
    const winnerModel = winnerIsA ? this.models[0] : this.models[1];
    const winnerText = winnerIsA ? deskAText : deskBText;

    const telemetry = [
      {
        model_id: this.models[0],
        desk_name: 'Desk A — Primary Broadcast Network',
        text: deskAText,
        elapsed_s: 4.2,
        completion_tokens: 168,
        prompt_tokens: 742,
        tok_per_sec: Number(speedA.toFixed(1)),
        status: 'ok',
      },
      {
        model_id: this.models[1],
        desk_name: 'Desk B — Olympic Analysis Desk',
        text: deskBText,
        elapsed_s: 5.1,
        completion_tokens: 181,
        prompt_tokens: 742,
        tok_per_sec: Number(speedB.toFixed(1)),
        status: 'ok',
      },
    ];

    const metrics = {
      [this.models[0]]: {
        next_match_accuracy_pct: 0,
        final_winner_accuracy_pct: 0,
        mean_brier_score: 0,
        avg_cqi_score: cqiA,
        avg_engagement_score: 84.2,
        avg_tok_per_sec: Number(speedA.toFixed(1)),
        total_hallucinations: 0,
      },
      [this.models[1]]: {
        next_match_accuracy_pct: 0,
        final_winner_accuracy_pct: 0,
        mean_brier_score: 0,
        avg_cqi_score: cqiB,
        avg_engagement_score: 88.1,
        avg_tok_per_sec: Number(speedB.toFixed(1)),
        total_hallucinations: 0,
      },
    };

    return {
      latest_over: {
        match_index: state.matchIndex,
        over_index: state.overIndex,
        hero_team: 'South Africa',
        opponent_team: opponent,
        phase,
        state_after: { runs: state.runs, wickets: state.wickets, balls: state.balls },
        winner_model: winnerModel,
        judge_verdict: `WINNER: ${winnerIsA ? 'A' : 'B'}`,
        surprise,
        telemetry,
        quality_metrics: {
          [this.models[0]]: { cqi_score: cqiA, engagement_score: 84 },
          [this.models[1]]: { cqi_score: cqiB, engagement_score: 88 },
        },
      },
      commentary_feed: [
        {
          model: winnerModel,
          desk_name: winnerIsA
            ? 'Desk A — Primary Broadcast Network'
            : 'Desk B — Olympic Analysis Desk',
          text: winnerText,
          cqi: winnerIsA ? cqiA : cqiB,
          eng: winnerIsA ? 84 : 88,
          toks: winnerIsA ? Number(speedA.toFixed(1)) : Number(speedB.toFixed(1)),
          over: state.overIndex,
        },
      ],
      metrics,
      head_to_head: {
        model_a: this.models[0],
        model_b: this.models[1],
        model_a_wins: state.modelAWins,
        model_b_wins: state.modelBWins,
        by_model: {
          [this.models[0]]: state.modelAWins,
          [this.models[1]]: state.modelBWins,
        },
      },
      predictions: [
        {
          model_id: this.models[0],
          desk_name: 'Desk A',
          prediction_type: 'NEXT_MATCH',
          predicted_team: 'South Africa',
          confidence_pct: 78,
        },
        {
          model_id: this.models[0],
          desk_name: 'Desk A',
          prediction_type: 'FINAL',
          predicted_team: 'South Africa',
          confidence_pct: 66,
        },
        {
          model_id: this.models[1],
          desk_name: 'Desk B',
          prediction_type: 'NEXT_MATCH',
          predicted_team: 'South Africa',
          confidence_pct: 82,
        },
        {
          model_id: this.models[1],
          desk_name: 'Desk B',
          prediction_type: 'FINAL',
          predicted_team: 'India',
          confidence_pct: 58,
        },
      ],
      tournament_progress: this.phases.map((item, index) => ({
        match_index: index + 1,
        phase: item,
        completed: index + 1 < state.matchIndex,
        is_current: index + 1 === state.matchIndex,
      })),
      run_metadata: {
        run_id: 'browser_demo_unofficial',
        prompt_version: 'v1.0-fixed',
        models_configured: [...this.models, this.models[1]],
        endpoints_by_role: {
          desk_a: 'OpenAI-compatible endpoint A',
          desk_b: 'OpenAI-compatible endpoint B',
          judge: 'Configured judge endpoint',
        },
      },
      venue_context: {
        weather: '82°F · Dry',
        crowd: 16840 + (state.tick % 9) * 37,
        traffic: 74 + (state.tick % 4),
        simulated: true,
      },
    };
  }
}
