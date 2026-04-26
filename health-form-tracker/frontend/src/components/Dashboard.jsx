/**
 * Dashboard.jsx — Real-time workout stats panel.
 * Displays rep count, phase, form quality, angle readouts,
 * processing latency, and connection status.
 */
import { useRef, useEffect } from 'react';
import './Dashboard.css';
import { playDing, playBuzz, speak } from '../utils/audio.js';

export default function Dashboard({ status, globalReps, isConnected, isReconnecting }) {
  const repRef = useRef(null);
  const prevGlobalReps = useRef(0);
  const prevPerfectForm = useRef(true);
  const prevWarnings = useRef([]);
  const lastBuzzTime = useRef(0);
  const statusState = status?.state ?? null;
  const statusElbowAngle = status?.elbow_angle ?? null;
  const statusPerfectForm = status?.perfect_form ?? true;
  const statusWarnings = status?.warnings;

  // Animate the rep counter on increment and play audio cue
  useEffect(() => {
    if (globalReps > prevGlobalReps.current) {
      const el = repRef.current;
      if (el) {
        el.classList.remove('dashboard__rep-pop');
        // Force reflow to restart animation
        void el.offsetWidth;
        el.classList.add('dashboard__rep-pop');
      }
      playDing();
      speak(globalReps.toString());
    }
    prevGlobalReps.current = globalReps;
  }, [globalReps]);

  // Play audio cue for form penalties
  useEffect(() => {
    if (!status) return;
    const activeStates = ['UP', 'DESCENDING', 'BOTTOM', 'ASCENDING'];
    const isActive = statusElbowAngle != null && activeStates.includes(statusState);
    const warnings = statusWarnings ?? [];
    
    const hasAbortedWarning = warnings.includes("Rep not counted: bad form");
    const hadAbortedWarning = prevWarnings.current.includes("Rep not counted: bad form");
    
    const now = Date.now();
    const canBuzz = (now - lastBuzzTime.current) > 2000;

    if (isActive && !status.perfect_form && prevPerfectForm.current) {
      if (canBuzz) {
        playBuzz();
        if (warnings.length > 0) {
          speak(warnings[0]);
        }
        lastBuzzTime.current = now;
      }
    } else if (hasAbortedWarning && !hadAbortedWarning) {
      if (canBuzz) {
        playBuzz();
        speak("Rep not counted");
        lastBuzzTime.current = now;
      }
    }
    
    prevPerfectForm.current = statusPerfectForm;
    prevWarnings.current = warnings;
  }, [status, statusElbowAngle, statusPerfectForm, statusState, statusWarnings]);

  const hasPerson = status?.elbow_angle != null;
  const repCount = globalReps;
  const phase = status?.state ?? 'PAUSED';
  const perfectForm = status?.perfect_form ?? false;
  const warnings = status?.warnings ?? [];
  const elbowAngle = status?.elbow_angle;
  const backAngle = status?.back_angle;
  const processingMs = status?.processing_ms;

  // Form evaluation is only meaningful during active pushup states
  const activeStates = ['UP', 'DESCENDING', 'BOTTOM', 'ASCENDING'];
  const isActive = hasPerson && activeStates.includes(phase);

  // Connection status dot
  let dotClass = 'dashboard__dot--disconnected';
  if (isConnected) dotClass = 'dashboard__dot--connected';
  else if (isReconnecting) dotClass = 'dashboard__dot--reconnecting';

  return (
    <aside className="dashboard" aria-label="Workout statistics">
      {/* Connection indicator */}
      <div className="dashboard__connection">
        <span className={`dashboard__dot ${dotClass}`} />
        <span className="dashboard__connection-label">
          {isConnected ? 'Connected' : isReconnecting ? 'Reconnecting...' : 'Disconnected'}
        </span>
      </div>

      {/* Rep counter */}
      <div className="dashboard__card dashboard__card--reps">
        <span className="dashboard__label">REPS</span>
        <span ref={repRef} className="dashboard__rep-count">{repCount}</span>
      </div>

      {/* Phase */}
      <div className="dashboard__card">
        <span className="dashboard__label">PHASE</span>
        <span className={`dashboard__phase-badge dashboard__phase-badge--${phase.toLowerCase()}`}>
          {hasPerson ? phase : (phase === 'PAUSED' ? 'WAITING' : phase)}
        </span>
      </div>

      {/* Form status */}
      <div className={`dashboard__card dashboard__card--form ${isActive ? (perfectForm ? 'dashboard__card--form-good' : 'dashboard__card--form-bad') : ''}`}>
        <span className="dashboard__label">FORM</span>
        <span className="dashboard__form-text">
          {!isActive ? '--' : perfectForm ? 'PERFECT' : 'ADJUST'}
        </span>
        {warnings.length > 0 && (
          <span className="dashboard__warning">! {warnings[0]}</span>
        )}
      </div>

      {/* Angles */}
      <div className="dashboard__angles">
        <div className="dashboard__card dashboard__card--small">
          <span className="dashboard__label">ELBOW</span>
          <span className="dashboard__angle-value">
            {elbowAngle != null ? `${Math.round(elbowAngle)}°` : '--'}
          </span>
        </div>
        <div className="dashboard__card dashboard__card--small">
          <span className="dashboard__label">BACK</span>
          <span className="dashboard__angle-value">
            {backAngle != null ? `${Math.round(backAngle)}°` : '--'}
          </span>
        </div>
      </div>

      {/* Processing latency */}
      <div className="dashboard__latency">
        {processingMs != null ? `${processingMs}ms` : '--'}
      </div>
    </aside>
  );
}
