/**
 * Web Speech API Voiceover Synthesizer
 * Speaks live AI broadcast commentary out loud with distinct voice profiles for Desk A vs Desk B.
 */
export class VoiceSynthEngine {
  constructor() {
    this.synth = window.speechSynthesis || null;
    this.enabled = false;
    this.voices = [];
    
    if (this.synth) {
      this.loadVoices();
      if (speechSynthesis.onvoiceschanged !== undefined) {
        speechSynthesis.onvoiceschanged = () => this.loadVoices();
      }
    }
  }

  loadVoices() {
    if (!this.synth) return;
    this.voices = this.synth.getVoices();
  }

  toggleVoice(state) {
    this.enabled = state !== undefined ? state : !this.enabled;
    if (!this.enabled && this.synth) {
      this.synth.cancel();
    }
    return this.enabled;
  }

  speakCommentary(text, desk = 'A') {
    if (!this.enabled || !this.synth || !text) return;

    // Cancel existing utterance
    this.synth.cancel();

    // Clean text snippet for speech
    const cleanText = text.replace(/NEXT_MATCH_PREDICTION:.*|FINAL_PREDICTION:.*/gi, '').trim();
    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText.slice(0, 180));
    utterance.rate = 1.05;

    if (desk === 'A') {
      utterance.pitch = 0.95; // Deep sports commentator
    } else {
      utterance.pitch = 1.15; // Energetic analytical commentator
    }

    // Assign English voice if available
    const enVoices = this.voices.filter(v => v.lang.startsWith('en'));
    if (enVoices.length > 0) {
      utterance.voice = desk === 'A' ? enVoices[0] : (enVoices[1] || enVoices[0]);
    }

    this.synth.speak(utterance);
  }
}
