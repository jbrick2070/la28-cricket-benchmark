import { StadiumCanvasEngine } from './stadiumCanvas.js';
import { AudioSynthEngine } from './audioSynth.js';
import { VoiceSynthEngine } from './voiceSynth.js';
import { DataManager } from './dataManager.js';

document.addEventListener('DOMContentLoaded', () => {
  // Initialize Engines
  const stadium = new StadiumCanvasEngine('stadium-canvas');
  const audio = new AudioSynthEngine();
  const voice = new VoiceSynthEngine();
  const dataMgr = new DataManager();

  // Tab Navigation Setup
  const tabs = document.querySelectorAll('.nav-tab');
  const panels = document.querySelectorAll('.tab-panel');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      const targetPanel = document.getElementById(`tab-${tab.dataset.tab}`);
      if (targetPanel) {
        targetPanel.classList.add('active');
      }

      if (tab.dataset.tab === 'stadium') {
        setTimeout(() => stadium.resizeCanvas(), 50);
      }
    });
  });

  // Camera Controls Setup
  const camBtns = document.querySelectorAll('.cam-btn');
  camBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      camBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      stadium.setCameraMode(btn.dataset.cam);
    });
  });

  // Manual Trigger Shot Button
  const triggerBtn = document.getElementById('simulate-shot-btn');
  if (triggerBtn) {
    triggerBtn.addEventListener('click', () => {
      const shots = ['six', 'four', 'wicket', 'dot'];
      const randomShot = shots[Math.floor(Math.random() * shots.length)];
      stadium.triggerDelivery(randomShot);

      audio.playBatCrack();
      if (randomShot === 'six' || randomShot === 'four') {
        setTimeout(() => audio.playCrowdCheer(), 200);
      }
    });
  }

  // Audio Toggle Button
  const audioBtn = document.getElementById('toggle-audio-btn');
  if (audioBtn) {
    audioBtn.addEventListener('click', () => {
      const isEnabled = audio.toggleAudio();
      audioBtn.querySelector('.btn-label').innerText = isEnabled ? 'Audio ON' : 'Audio OFF';
      audioBtn.querySelector('.icon').innerText = isEnabled ? '🔊' : '🔇';
    });
  }

  // TTS Voiceover Toggle Button
  const ttsBtn = document.getElementById('toggle-tts-btn');
  if (ttsBtn) {
    ttsBtn.addEventListener('click', () => {
      const isEnabled = voice.toggleVoice();
      ttsBtn.querySelector('.btn-label').innerText = isEnabled ? 'Voice ON' : 'Voice OFF';
      ttsBtn.querySelector('.icon').innerText = isEnabled ? '🎙️' : '🔇';
    });
  }

  // Copy OBS URL Buttons
  const copyBtns = document.querySelectorAll('.btn-copy');
  copyBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const url = btn.dataset.url;
      navigator.clipboard.writeText(url);
      const originalText = btn.innerText;
      btn.innerText = 'Copied!';
      btn.style.background = '#10b981';
      btn.style.color = '#000';
      setTimeout(() => {
        btn.innerText = originalText;
        btn.style.background = '';
        btn.style.color = '';
      }, 1500);
    });
  });

  // Data Updates Callback
  dataMgr.onDataUpdate((data, isBackend) => {
    // 1. Update Header Status Badge
    const badge = document.getElementById('data-mode-badge');
    const modeText = document.getElementById('mode-text');
    if (badge && modeText) {
      if (isBackend) {
        badge.style.background = 'rgba(16, 185, 129, 0.12)';
        badge.style.borderColor = 'rgba(16, 185, 129, 0.3)';
        badge.style.color = '#10b981';
        modeText.innerText = 'Live Python Backend';
      } else {
        badge.style.background = 'rgba(245, 158, 11, 0.12)';
        badge.style.borderColor = 'rgba(245, 158, 11, 0.3)';
        badge.style.color = '#f59e0b';
        modeText.innerText = 'Browser Simulation Mode';
      }
    }

    // 2. Update Live Stadium Score & HUD
    if (data.latest_over) {
      const lo = data.latest_over;
      const scoreRuns = document.getElementById('match-score-runs');
      const oversVal = document.getElementById('match-overs-val');
      const matchTitle = document.getElementById('stadium-match-title');
      const phaseBadge = document.getElementById('current-phase-badge');

      if (scoreRuns) scoreRuns.innerText = `${lo.state_after.runs}/${lo.state_after.wickets}`;
      if (oversVal) oversVal.innerText = `Over ${lo.over_index} / 20`;
      if (matchTitle) matchTitle.innerText = `${lo.hero_team} vs ${lo.opponent_team}`;
      if (phaseBadge) phaseBadge.innerText = lo.phase;

      // Surprise Banner Alert
      const surpriseBanner = document.getElementById('surprise-banner');
      const surpriseText = document.getElementById('surprise-text');
      if (surpriseBanner && surpriseText) {
        if (lo.surprise) {
          surpriseText.innerText = lo.surprise;
          surpriseBanner.style.display = 'flex';
        } else {
          surpriseBanner.style.display = 'none';
        }
      }

      // Trigger Canvas Ball Animation on over increment
      const shotTypes = ['six', 'four', 'dot', 'wicket'];
      const shot = lo.state_after.runs % 2 === 0 ? 'six' : 'four';
      stadium.triggerDelivery(shot);
      audio.playBatCrack();
    }

    // 3. Update Winning Commentary & Head-to-Head Tally
    if (data.commentary_feed && data.commentary_feed.length > 0) {
      const topComm = data.commentary_feed[0];
      const winText = document.getElementById('winning-commentary-text');
      const winDesk = document.getElementById('winning-desk-name');
      const winCqi = document.getElementById('winning-cqi');
      const winEng = document.getElementById('winning-engagement');
      const winToks = document.getElementById('winning-speed');

      if (winText) winText.innerText = `"${topComm.text}"`;
      if (winDesk) winDesk.innerText = topComm.desk_name;
      if (winCqi) winCqi.innerText = `CQI: ${topComm.cqi}/100`;
      if (winEng) winEng.innerText = `Engagement: ${topComm.eng}%`;
      if (winToks) winToks.innerText = `${topComm.toks} tok/s`;

      // Voiceover Speech
      const deskID = topComm.desk_name.includes('A') || topComm.desk_name.includes('2.5') ? 'A' : 'B';
      voice.speakCommentary(topComm.text, deskID);

      // Desk Tabs Texts
      const deskAText = document.getElementById('desk-a-text');
      const deskBText = document.getElementById('desk-b-text');
      if (deskAText && deskID === 'A') deskAText.innerText = topComm.text;
      if (deskBText && deskID === 'B') deskBText.innerText = topComm.text;
    }

    // 4. Update Head-to-Head Victories Bar
    if (data.head_to_head) {
      const aWins = data.head_to_head.model_a_wins || 0;
      const bWins = data.head_to_head.model_b_wins || 0;
      const total = (aWins + bWins) || 1;
      const pctA = Math.round((aWins / total) * 100);
      const pctB = 100 - pctA;

      const barA = document.getElementById('h2h-bar-a');
      const barB = document.getElementById('h2h-bar-b');
      if (barA) {
        barA.style.width = `${pctA}%`;
        barA.innerText = `Desk A (${pctA}%)`;
      }
      if (barB) {
        barB.style.width = `${pctB}%`;
        barB.innerText = `Desk B (${pctB}%)`;
      }
    }

    // 5. Update Telemetry Radar & Predictions
    if (data.metrics) {
      const mA = data.metrics['qwen/qwen2.5-coder-14b'];
      const mB = data.metrics['qwen/qwen3-coder-30b'];

      if (mA) {
        document.getElementById('desk-a-cqi').innerText = mA.avg_cqi_score || 78;
        document.getElementById('desk-a-eng').innerText = mA.avg_engagement_score || 83;
        document.getElementById('desk-a-brier').innerText = mA.mean_brier_score || 0.035;
        document.getElementById('desk-a-toks').innerText = mA.tok_per_sec || 42.1;
      }
      if (mB) {
        document.getElementById('desk-b-cqi').innerText = mB.avg_cqi_score || 86;
        document.getElementById('desk-b-eng').innerText = mB.avg_engagement_score || 88;
        document.getElementById('desk-b-brier').innerText = mB.mean_brier_score || 0.024;
        document.getElementById('desk-b-toks').innerText = mB.tok_per_sec || 38.4;
      }
    }
  });
});
