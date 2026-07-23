import { StadiumCanvasEngine } from './stadiumCanvas.js';
import { AudioSynthEngine } from './audioSynth.js';
import { VoiceSynthEngine } from './voiceSynth.js';
import { DataManager } from './dataManager.js';

const byId = (id) => document.getElementById(id);
const setText = (id, value) => {
  const element = byId(id);
  if (element && value !== undefined && value !== null) element.textContent = String(value);
};
const modelLabel = (modelId = '') => modelId.split('/').pop() || modelId || 'Unassigned model';
const numberOr = (value, fallback = 0) => {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
};

const TEAM_CODES = {
  'South Africa': 'RSA',
  Australia: 'AUS',
  'Great Britain (via England)': 'GBR',
  'Great Britain': 'GBR',
  India: 'IND',
  'Qualifier 5': 'Q05',
  'Qualifier 6': 'Q06',
};

document.addEventListener('DOMContentLoaded', () => {
  const stadium = new StadiumCanvasEngine('stadium-canvas');
  const audio = new AudioSynthEngine();
  const voice = new VoiceSynthEngine();
  const dataManager = new DataManager();
  let previousOverKey = '';

  document.querySelectorAll('.nav-tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.nav-tab').forEach((item) => item.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach((panel) => panel.classList.remove('active'));
      tab.classList.add('active');
      byId(`tab-${tab.dataset.tab}`)?.classList.add('active');
      if (tab.dataset.tab === 'stadium') window.setTimeout(() => stadium.resizeCanvas(), 50);
    });
  });

  document.querySelectorAll('.cam-btn').forEach((button) => {
    button.addEventListener('click', () => {
      document.querySelectorAll('.cam-btn').forEach((item) => item.classList.remove('active'));
      button.classList.add('active');
      stadium.setCameraMode(button.dataset.cam);
    });
  });

  byId('simulate-shot-btn')?.addEventListener('click', () => {
    const shots = ['six', 'four', 'wicket', 'dot'];
    const shot = shots[Math.floor(Math.random() * shots.length)];
    stadium.triggerDelivery(shot);
    audio.playBatCrack();
    if (shot === 'six' || shot === 'four') window.setTimeout(() => audio.playCrowdCheer(), 180);
  });

  byId('toggle-audio-btn')?.addEventListener('click', (event) => {
    const enabled = audio.toggleAudio();
    event.currentTarget.querySelector('.btn-label').textContent = enabled ? 'Audio on' : 'Audio off';
    event.currentTarget.querySelector('.icon').textContent = enabled ? '◖))' : '×';
  });

  byId('toggle-tts-btn')?.addEventListener('click', (event) => {
    const enabled = voice.toggleVoice();
    event.currentTarget.querySelector('.btn-label').textContent = enabled ? 'Voice on' : 'Voice off';
    event.currentTarget.querySelector('.icon').textContent = enabled ? '◉' : '○';
  });

  document.querySelectorAll('.btn-copy').forEach((button) => {
    button.addEventListener('click', async () => {
      const original = button.querySelector('b')?.textContent || button.textContent;
      try {
        await navigator.clipboard.writeText(button.dataset.url);
        if (button.querySelector('b')) button.querySelector('b').textContent = 'Copied to clipboard';
        else button.textContent = 'Copied to clipboard';
      } catch {
        if (button.querySelector('b')) button.querySelector('b').textContent = button.dataset.url;
      }
      window.setTimeout(() => {
        if (button.querySelector('b')) button.querySelector('b').textContent = original;
      }, 1600);
    });
  });

  dataManager.onDataUpdate((data, isBackend) => {
    updateConnectionState(isBackend);
    updateRunIdentity(data);
    updateVenueContext(data.venue_context);
    updateMatchWorld(data, stadium, audio, previousOverKey, (key) => {
      previousOverKey = key;
    });
    updateCommentary(data, voice);
    updateHeadToHead(data);
    updateMetrics(data);
    updatePredictions(data);
    updateJourney(data);
    updateProvenance(data);
  });
});

function updateConnectionState(isBackend) {
  const badge = byId('data-mode-badge');
  if (!badge) return;
  badge.style.color = isBackend ? 'var(--green)' : 'var(--gold)';
  badge.style.borderColor = isBackend
    ? 'rgba(145, 242, 165, .3)'
    : 'rgba(255, 178, 95, .35)';
  setText('mode-text', isBackend ? 'Live benchmark ledger' : 'Browser demo · simulated');
}

function getConfiguredModels(data) {
  const configured = data.run_metadata?.models_configured || [];
  const metricModels = Object.keys(data.metrics || {});
  const h2hModels = [data.head_to_head?.model_a, data.head_to_head?.model_b].filter(Boolean);
  const merged = [...configured, ...metricModels, ...h2hModels].filter(Boolean);
  return [...new Set(merged)].slice(0, 2);
}

function updateRunIdentity(data) {
  const [modelA = 'Model A', modelB = 'Model B'] = getConfiguredModels(data);
  setText('desk-a-model', modelLabel(modelA));
  setText('desk-b-model', modelLabel(modelB));
  setText('sidebar-model-a', modelLabel(modelA));
  setText('sidebar-model-b', modelLabel(modelB));
}

function updateVenueContext(context) {
  if (!context) return;
  setText('venue-weather', context.weather);
  setText('venue-crowd', numberOr(context.crowd).toLocaleString('en-US'));
  setText('venue-traffic', `${numberOr(context.traffic)} / 100`);
}

function updateMatchWorld(data, stadium, audio, previousOverKey, rememberOverKey) {
  const latest = data.latest_over;
  if (!latest?.state_after) return;
  const hero = latest.hero_team || 'South Africa';
  const opponent = latest.opponent_team || 'Opponent';
  const state = latest.state_after;
  const overKey = `${latest.match_index}-${latest.over_index}`;

  setText('stadium-match-title', `${hero} vs ${opponent}`);
  setText('hero-name', hero);
  setText('hero-code', TEAM_CODES[hero] || hero.slice(0, 3).toUpperCase());
  setText('opp-name', opponent);
  setText('opp-code', TEAM_CODES[opponent] || opponent.slice(0, 3).toUpperCase());
  setText('match-score-runs', `${numberOr(state.runs)}/${numberOr(state.wickets)}`);
  setText('match-overs-val', `OVER ${numberOr(latest.over_index)} / 20`);
  setText('current-phase-badge', latest.phase || `Match ${latest.match_index}`);
  setText('winning-over-num', latest.over_index);

  const surprise = byId('surprise-banner');
  if (surprise) {
    surprise.hidden = !latest.surprise;
    if (latest.surprise) setText('surprise-text', latest.surprise);
  }

  const telemetry = latest.telemetry || [];
  if (telemetry[0]) {
    setText('desk-a-text', telemetry[0].text);
    setText('sidebar-speed-a', `${numberOr(telemetry[0].tok_per_sec).toFixed(1)} tok/s`);
  }
  if (telemetry[1]) {
    setText('desk-b-text', telemetry[1].text);
    setText('sidebar-speed-b', `${numberOr(telemetry[1].tok_per_sec).toFixed(1)} tok/s`);
  }

  updateBallSequence(state, latest.over_index);
  if (overKey !== previousOverKey) {
    const wicket = numberOr(state.wickets);
    const shot = wicket > 0 && numberOr(latest.over_index) % 5 === 0
      ? 'wicket'
      : numberOr(state.runs) % 3 === 0
        ? 'six'
        : 'four';
    stadium.triggerDelivery(shot);
    audio.playBatCrack();
    rememberOverKey(overKey);
  }
}

function updateBallSequence(state, overIndex) {
  const container = byId('balls-sequence-container');
  if (!container) return;
  const seed = numberOr(state.runs) + numberOr(state.wickets) * 13 + numberOr(overIndex) * 7;
  const outcomes = [0, 1, 2, 4, 6, 'W'];
  const values = Array.from({ length: 6 }, (_, index) => outcomes[(seed + index * 5) % outcomes.length]);
  container.replaceChildren(
    ...values.map((value, index) => {
      const element = document.createElement('span');
      element.className = 'ball-dot';
      if (value === 4) element.classList.add('dot-four');
      if (value === 6) element.classList.add('dot-six');
      if (value === 'W') element.classList.add('dot-wicket');
      if (index === 5) element.classList.add('current');
      element.textContent = value === 0 ? '•' : String(value);
      return element;
    }),
  );
}

function updateCommentary(data, voice) {
  const top = data.commentary_feed?.[0];
  if (!top) return;
  setText('winning-commentary-text', top.text);
  setText('winning-desk-name', top.desk_name || modelLabel(top.model));
  setText('winning-cqi', `CQI ${numberOr(top.cqi)}`);
  setText('winning-engagement', `ENG ${numberOr(top.eng)}`);
  setText('winning-speed', `${numberOr(top.toks).toFixed(1)} tok/s`);

  const [modelA] = getConfiguredModels(data);
  const deskId = top.model === modelA ? 'A' : 'B';
  voice.speakCommentary(top.text, deskId);
}

function updateHeadToHead(data) {
  const h2h = data.head_to_head;
  if (!h2h) return;
  const winsA = numberOr(h2h.model_a_wins);
  const winsB = numberOr(h2h.model_b_wins);
  const total = winsA + winsB;
  const pctA = total ? Math.round((winsA / total) * 100) : 50;
  const pctB = 100 - pctA;
  const barA = byId('h2h-bar-a');
  const barB = byId('h2h-bar-b');
  if (barA) {
    barA.style.width = `${pctA}%`;
    barA.textContent = `A ${pctA}%`;
  }
  if (barB) {
    barB.style.width = `${pctB}%`;
    barB.textContent = `B ${pctB}%`;
  }
}

function updateMetrics(data) {
  const [modelA, modelB] = getConfiguredModels(data);
  const metricsA = data.metrics?.[modelA] || {};
  const metricsB = data.metrics?.[modelB] || {};
  updateModelMetricSet('a', metricsA);
  updateModelMetricSet('b', metricsB);

  const cqiA = numberOr(metricsA.avg_cqi_score);
  const cqiB = numberOr(metricsB.avg_cqi_score);
  const speedA = numberOr(metricsA.avg_tok_per_sec ?? metricsA.tok_per_sec);
  const speedB = numberOr(metricsB.avg_tok_per_sec ?? metricsB.tok_per_sec);
  updateBar('radar-acc-next-a', numberOr(metricsA.next_match_accuracy_pct), 'A');
  updateBar('radar-acc-next-b', numberOr(metricsB.next_match_accuracy_pct), 'B');
  updateBar('radar-acc-gold-a', numberOr(metricsA.final_winner_accuracy_pct), 'A');
  updateBar('radar-acc-gold-b', numberOr(metricsB.final_winner_accuracy_pct), 'B');
  updateBar('radar-cqi-a', cqiA, 'A');
  updateBar('radar-cqi-b', cqiB, 'B');
  updateBar('radar-speed-a', Math.min(100, speedA * 1.7), 'A', `${speedA.toFixed(1)} tok/s`);
  updateBar('radar-speed-b', Math.min(100, speedB * 1.7), 'B', `${speedB.toFixed(1)} tok/s`);

  const hallucinations = numberOr(metricsA.total_hallucinations)
    + numberOr(metricsB.total_hallucinations);
  setText('hallucination-count-tag', `${hallucinations} flagged`);
}

function updateModelMetricSet(desk, metrics) {
  const speed = numberOr(metrics.avg_tok_per_sec ?? metrics.tok_per_sec);
  setText(`desk-${desk}-cqi`, numberOr(metrics.avg_cqi_score) || '—');
  setText(`desk-${desk}-eng`, numberOr(metrics.avg_engagement_score) || '—');
  setText(
    `desk-${desk}-brier`,
    metrics.mean_brier_score === undefined ? '—' : numberOr(metrics.mean_brier_score).toFixed(3),
  );
  setText(`desk-${desk}-toks`, speed ? speed.toFixed(1) : '—');
  setText(`sidebar-speed-${desk}`, speed ? `${speed.toFixed(1)} tok/s` : '—');
}

function updateBar(id, percentage, prefix, explicitLabel) {
  const bar = byId(id);
  if (!bar) return;
  const width = Math.max(4, Math.min(100, percentage));
  bar.style.width = `${width}%`;
  bar.textContent = explicitLabel ? `${prefix} · ${explicitLabel}` : `${prefix} · ${percentage.toFixed(0)}%`;
}

function updatePredictions(data) {
  const [modelA, modelB] = getConfiguredModels(data);
  const predictions = data.predictions || [];
  updatePredictionDesk('a', modelA, predictions);
  updatePredictionDesk('b', modelB, predictions);
}

function updatePredictionDesk(desk, modelId, predictions) {
  const forModel = predictions.filter((prediction) => prediction.model_id === modelId);
  const next = [...forModel].reverse().find((prediction) => prediction.prediction_type === 'NEXT_MATCH');
  const final = [...forModel].reverse().find((prediction) => prediction.prediction_type === 'FINAL');
  if (next) setText(`desk-${desk}-pred-next`, `${next.predicted_team} · ${numberOr(next.confidence_pct)}%`);
  if (final) setText(`desk-${desk}-pred-final`, `${final.predicted_team} · ${numberOr(final.confidence_pct)}%`);
}

function updateJourney(data) {
  const activeMatch = numberOr(data.latest_over?.match_index, 1);
  document.querySelectorAll('.route-stop').forEach((stop, index) => {
    stop.classList.toggle('complete', index + 1 < activeMatch);
    stop.classList.toggle('active', index + 1 === activeMatch);
  });
}

function updateProvenance(data) {
  const metadata = data.run_metadata || {};
  setText('spec-run-id', metadata.run_id || 'Awaiting run');
  setText('spec-prompt-version', metadata.prompt_version || 'Fixed baseline');
  setText('spec-endpoint-a', metadata.endpoints_by_role?.desk_a || 'Configurable');
  setText('spec-endpoint-b', metadata.endpoints_by_role?.desk_b || 'Configurable');
}
