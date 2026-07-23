/**
 * Web Audio API Sound Effects & Stadium Ambiance Synthesizer
 * Zero external audio files required — synthesizes sound dynamically in browser.
 */
export class AudioSynthEngine {
  constructor() {
    this.ctx = null;
    this.enabled = true;
    this.crowdNode = null;
    this.crowdGain = null;
  }

  initContext() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      this.ctx = new AudioCtx();
    }
    if (this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  toggleAudio(state) {
    this.enabled = state !== undefined ? state : !this.enabled;
    if (this.enabled) {
      this.startCrowdAmbiance();
    } else if (this.crowdGain) {
      this.crowdGain.gain.setTargetAtTime(0, this.ctx.currentTime, 0.2);
    }
    return this.enabled;
  }

  // Synthesize Bat Crack (High Frequency Click + Wood Resonance)
  playBatCrack() {
    if (!this.enabled) return;
    this.initContext();
    const ctx = this.ctx;
    const now = ctx.currentTime;

    // Noise click
    const bufferSize = ctx.sampleRate * 0.05;
    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      data[i] = (Math.random() * 2 - 1) * Math.exp(-i / (bufferSize * 0.1));
    }

    const noise = ctx.createBufferSource();
    noise.buffer = buffer;

    const filter = ctx.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.setValueAtTime(1800, now);
    filter.Q.setValueAtTime(3.0, now);

    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.8, now);
    gain.gain.exponentialRampToValueAtTime(0.01, now + 0.05);

    noise.connect(filter);
    filter.connect(gain);
    gain.connect(ctx.destination);

    noise.start(now);
  }

  // Synthesize Boundary / Wicket Crowd Cheer Roar
  playCrowdCheer() {
    if (!this.enabled) return;
    this.initContext();
    const ctx = this.ctx;
    const now = ctx.currentTime;
    const duration = 2.5;

    const bufferSize = ctx.sampleRate * duration;
    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    let lastOut = 0.0;

    // Pink noise for crowd cheer
    for (let i = 0; i < bufferSize; i++) {
      const white = Math.random() * 2 - 1;
      data[i] = (lastOut + 0.02 * white) / 1.02;
      lastOut = data[i];
    }

    const crowd = ctx.createBufferSource();
    crowd.buffer = buffer;

    const filter = ctx.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.setValueAtTime(400, now);
    filter.frequency.exponentialRampToValueAtTime(1200, now + 0.8);
    filter.frequency.exponentialRampToValueAtTime(300, now + duration);

    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.01, now);
    gain.gain.linearRampToValueAtTime(0.6, now + 0.4);
    gain.gain.exponentialRampToValueAtTime(0.01, now + duration);

    crowd.connect(filter);
    filter.connect(gain);
    gain.connect(ctx.destination);

    crowd.start(now);
  }

  // Ongoing Low Background Stadium Ambiance
  startCrowdAmbiance() {
    if (!this.enabled) return;
    this.initContext();
    if (this.crowdNode) return;

    const ctx = this.ctx;
    const bufferSize = ctx.sampleRate * 2.0;
    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      data[i] = Math.random() * 2 - 1;
    }

    this.crowdNode = ctx.createBufferSource();
    this.crowdNode.buffer = buffer;
    this.crowdNode.loop = true;

    const filter = ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.value = 350;

    this.crowdGain = ctx.createGain();
    this.crowdGain.gain.setValueAtTime(0.08, ctx.currentTime);

    this.crowdNode.connect(filter);
    filter.connect(this.crowdGain);
    this.crowdGain.connect(ctx.destination);

    this.crowdNode.start();
  }
}
