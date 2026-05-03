/**
 * Dashboard.jsx - Real-time workout stats panel.
 */
import { useRef, useEffect } from 'react';
import './Dashboard.css';
import { playDing, playBuzz, speak } from '../utils/audio.js';
import { EXERCISES } from '../utils/sessionStorage.js';

const ACTIVE_STATES = ['UP', 'DESCENDING', 'BOTTOM', 'ASCENDING', 'STANDING'];
const FAULT_COOLDOWN_MS = 3500;

function formatPhase(phase) {
  if (phase === 'PAUSED') return 'WAITING';
  return phase;
}

function formatMetric(value, suffix = '') {
  return value == null ? '--' : `${value}${suffix}`;
}

export default function Dashboard({ status, exercise, globalReps, isConnected, isReconnecting, audioEnabled }) {
  const repRef = useRef(null);
  const prevGlobalReps = useRef(globalReps);
  const prevFaultCodes = useRef([]);
  const lastFaultSpokenAt = useRef({});

  const phase = status?.state ?? 'PAUSED';
  const faults = status?.faults ?? [];
  const primaryFault = faults[0] ?? null;
  const warnings = status?.warnings ?? [];
  const calibration = status?.calibration ?? { complete: false, progress: 0, message: 'Waiting for camera' };
  const setupGuidance = status?.setup_guidance;
  const repQuality = status?.rep_quality;
  const hasAngles = status?.elbow_angle != null || status?.knee_angle != null;
  const perfectForm = status?.perfect_form ?? false;
  const isActive = hasAngles && ACTIVE_STATES.includes(phase);

  useEffect(() => {
    if (globalReps > prevGlobalReps.current) {
      const el = repRef.current;
      if (el) {
        el.classList.remove('dashboard__rep-pop');
        void el.offsetWidth;
        el.classList.add('dashboard__rep-pop');
      }
      if (audioEnabled) {
        playDing();
        speak(globalReps.toString());
      }
    }
    prevGlobalReps.current = globalReps;
  }, [audioEnabled, globalReps]);

  useEffect(() => {
    if (!audioEnabled || faults.length === 0) {
      prevFaultCodes.current = faults.map((fault) => fault.code);
      return;
    }

    const now = Date.now();
    const currentCodes = faults.map((fault) => fault.code);
    const faultToSpeak = faults.find((fault) => {
      const lastSpokenAt = lastFaultSpokenAt.current[fault.code] ?? 0;
      return !prevFaultCodes.current.includes(fault.code) || now - lastSpokenAt > FAULT_COOLDOWN_MS;
    });

    if (faultToSpeak && faultToSpeak.severity !== 'info') {
      playBuzz();
      speak(faultToSpeak.message);
      lastFaultSpokenAt.current[faultToSpeak.code] = now;
    }

    prevFaultCodes.current = currentCodes;
  }, [audioEnabled, faults]);

  let dotClass = 'dashboard__dot--disconnected';
  if (isConnected) dotClass = 'dashboard__dot--connected';
  else if (isReconnecting) dotClass = 'dashboard__dot--reconnecting';

  const depthMetric = exercise === 'squat'
    ? formatMetric(repQuality?.min_knee_angle, 'deg')
    : formatMetric(repQuality?.min_elbow_angle, 'deg');
  const alignmentMetric = exercise === 'squat'
    ? formatMetric(repQuality?.min_torso_angle, 'deg')
    : formatMetric(repQuality?.min_back_angle, 'deg');

  return (
    <aside className="dashboard" aria-label="Workout statistics">
      <div className="dashboard__connection">
        <span className={`dashboard__dot ${dotClass}`} />
        <span className="dashboard__connection-label">
          {isConnected ? 'Connected' : isReconnecting ? 'Reconnecting...' : 'Disconnected'}
        </span>
      </div>

      <div className="dashboard__card dashboard__card--reps">
        <span className="dashboard__label">{EXERCISES[exercise] ?? 'Exercise'}</span>
        <span ref={repRef} className="dashboard__rep-count">{globalReps}</span>
      </div>

      <div className="dashboard__card">
        <span className="dashboard__label">Calibration</span>
        <div className="dashboard__progress" aria-label="Calibration progress">
          <span
            className="dashboard__progress-fill"
            style={{ width: `${Math.round((calibration.progress ?? 0) * 100)}%` }}
          />
        </div>
        <span className="dashboard__hint">
          {calibration.complete ? 'Ready' : calibration.message}
        </span>
      </div>

      <div className="dashboard__card">
        <span className="dashboard__label">Phase</span>
        <span className={`dashboard__phase-badge dashboard__phase-badge--${phase.toLowerCase()}`}>
          {formatPhase(phase)}
        </span>
      </div>

      <div className={`dashboard__card dashboard__card--form ${isActive ? (perfectForm ? 'dashboard__card--form-good' : 'dashboard__card--form-bad') : ''}`}>
        <span className="dashboard__label">Form</span>
        <span className="dashboard__form-text">
          {!isActive ? '--' : perfectForm ? 'PERFECT' : 'ADJUST'}
        </span>
        {(primaryFault || setupGuidance || warnings[0]) && (
          <span className="dashboard__warning">
            {primaryFault?.message ?? setupGuidance ?? warnings[0]}
          </span>
        )}
      </div>

      <div className="dashboard__angles">
        <div className="dashboard__card dashboard__card--small">
          <span className="dashboard__label">{exercise === 'squat' ? 'KNEE' : 'ELBOW'}</span>
          <span className="dashboard__angle-value">
            {exercise === 'squat'
              ? formatMetric(status?.knee_angle == null ? null : Math.round(status.knee_angle), 'deg')
              : formatMetric(status?.elbow_angle == null ? null : Math.round(status.elbow_angle), 'deg')}
          </span>
        </div>
        <div className="dashboard__card dashboard__card--small">
          <span className="dashboard__label">{exercise === 'squat' ? 'TORSO' : 'BACK'}</span>
          <span className="dashboard__angle-value">
            {formatMetric(status?.back_angle == null ? null : Math.round(status.back_angle), 'deg')}
          </span>
        </div>
      </div>

      <div className="dashboard__card dashboard__card--quality">
        <span className="dashboard__label">Last Rep</span>
        <div className="dashboard__quality-grid">
          <span>Depth</span>
          <strong>{depthMetric}</strong>
          <span>Alignment</span>
          <strong>{alignmentMetric}</strong>
          <span>Duration</span>
          <strong>{formatMetric(repQuality?.duration_ms, 'ms')}</strong>
        </div>
      </div>

      <div className="dashboard__latency">
        {status?.processing_ms != null ? `${status.processing_ms}ms` : '--'}
      </div>
    </aside>
  );
}
