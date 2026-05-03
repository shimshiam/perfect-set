/**
 * SessionLog.jsx - Mixed exercise session history and JSON export.
 */
import './SessionLog.css';
import { EXERCISES } from '../utils/sessionStorage.js';

export default function SessionLog({ session, activeExercise, onResetSession }) {
  const entries = session.events;
  const activeTotals = session.totals[activeExercise] ?? { completedReps: 0, abortedReps: 0 };

  const formatTime = (ts) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const exportSession = () => {
    if (entries.length === 0) return;
    const payload = {
      version: session.version,
      activeExercise: session.activeExercise,
      totals: session.totals,
      events: entries,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const dlAnchorElem = document.createElement('a');
    dlAnchorElem.setAttribute('href', url);
    dlAnchorElem.setAttribute('download', `perfect-set-session-${Date.now()}.json`);
    document.body.appendChild(dlAnchorElem);
    dlAnchorElem.click();
    document.body.removeChild(dlAnchorElem);
    URL.revokeObjectURL(url);
  };

  return (
    <section className="session-log" aria-label="Session rep history">
      <div className="session-log__header">
        <div>
          <h2 className="session-log__title">Session Log</h2>
          <p className="session-log__summary">
            {EXERCISES[activeExercise]}: {activeTotals.completedReps} counted / {activeTotals.abortedReps} rejected
          </p>
        </div>
        {entries.length > 0 && (
          <div className="session-log__actions">
            <button
              className="session-log__export-btn"
              onClick={exportSession}
              type="button"
              title="Export session data to JSON"
            >
              Export
            </button>
            <button
              className="session-log__reset-btn"
              onClick={onResetSession}
              type="button"
              title="Clear the saved session from this browser"
            >
              New
            </button>
          </div>
        )}
      </div>
      {entries.length === 0 ? (
        <p className="session-log__empty">No reps recorded yet. Start your set.</p>
      ) : (
        <ul className="session-log__list">
          {entries.map((entry) => (
            <li key={entry.id} className="session-log__item">
              <div className="session-log__main">
                <span className="session-log__rep-number">
                  {EXERCISES[entry.exercise]} {entry.attempt}
                </span>
                <span className="session-log__time">{formatTime(entry.timestamp)}</span>
              </div>
              <span className={`session-log__form-icon ${entry.result === 'completed' ? 'session-log__form-icon--good' : 'session-log__form-icon--bad'}`}>
                {entry.result === 'completed' ? 'OK' : 'X'}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
