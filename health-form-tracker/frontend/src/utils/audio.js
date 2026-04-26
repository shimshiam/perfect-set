/**
 * audio.js — Web Audio API utilities for real-time form feedback.
 */

// Initialize AudioContext lazily to comply with browser autoplay policies
let audioCtx = null;

function getAudioContext() {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
  return audioCtx;
}

export function initAudio() {
  const ctx = getAudioContext();
  if (ctx.state === 'suspended') {
    ctx.resume();
  }
  if ('speechSynthesis' in window) {
    // Speak empty string to warm up TTS on user interaction
    const u = new SpeechSynthesisUtterance('');
    window.speechSynthesis.speak(u);
  }
}

export function playDing() {
  const ctx = getAudioContext();
  if (ctx.state === 'suspended') {
    ctx.resume();
  }
  
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  
  osc.type = 'sine';
  osc.frequency.setValueAtTime(880, ctx.currentTime); // A5
  osc.frequency.exponentialRampToValueAtTime(440, ctx.currentTime + 0.5);
  
  gain.gain.setValueAtTime(0.5, ctx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);
  
  osc.connect(gain);
  gain.connect(ctx.destination);
  
  osc.start();
  osc.stop(ctx.currentTime + 0.5);
}

export function playBuzz() {
  const ctx = getAudioContext();
  if (ctx.state === 'suspended') {
    ctx.resume();
  }
  
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  
  osc.type = 'sawtooth';
  osc.frequency.setValueAtTime(150, ctx.currentTime);
  
  gain.gain.setValueAtTime(0.3, ctx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
  
  osc.connect(gain);
  gain.connect(ctx.destination);
  
  osc.start();
  osc.stop(ctx.currentTime + 0.3);
}

/**
 * Uses Web Speech API to provide verbal coaching.
 */
export function speak(text) {
  if (!('speechSynthesis' in window)) return;
  
  // Cancel any currently speaking text to give immediate feedback
  window.speechSynthesis.cancel();
  
  const utterance = new SpeechSynthesisUtterance(text);
  // Slightly faster rate sounds more energetic/coach-like
  utterance.rate = 1.15;
  utterance.pitch = 1.0;
  
  window.speechSynthesis.speak(utterance);
}
