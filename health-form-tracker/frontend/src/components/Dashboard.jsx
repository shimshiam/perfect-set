/**
 * Dashboard.jsx — Real-time workout stats panel.
 * Displays rep count, phase, form quality, angle readouts,
 * processing latency, and connection status.
 */
import { useRef, useEffect } from 'react';
import './Dashboard.css';

export default function Dashboard({ status, isConnected, isReconnecting }) {
  const repRef = useRef(null);
  const prevRepCount = useRef(0);

  // Animate the rep counter on increment
  useEffect(() => {
    if (!status) return;
    if (status.rep_count > prevRepCount.current) {
      const el = repRef.current;
      if (el) {
        el.classList.remove('dashboard__rep-pop');
        // Force reflow to restart animation
        void el.offsetWidth;
        el.classList.add('dashboard__rep-pop');
      }
    }
    prevRepCount.current = status.rep_count;
  }, [status?.rep_count]);

  const hasPerson = status?.elbow_angle != null;
  const repCount = status?.rep_count ?? 0;
  const phase = status?.state ?? 'PAUSED';
  const perfectForm = status?.perfect_form ?? false;
  const warnings = status?.warnings ?? [];
  const elbowAngle = status?.elbow_angle;
  const backAngle = status?.back_angle;
  const processingMs = status?.processing_ms;

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
          {hasPerson ? phase : 'WAITING'}
        </span>
      </div>

      {/* Form status */}
      <div className={`dashboard__card dashboard__card--form ${hasPerson ? (perfectForm ? 'dashboard__card--form-good' : 'dashboard__card--form-bad') : ''}`}>
        <span className="dashboard__label">FORM</span>
        <span className="dashboard__form-text">
          {!hasPerson ? '--' : perfectForm ? 'PERFECT' : 'ADJUST'}
        </span>
        {warnings.length > 0 && hasPerson && (
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
