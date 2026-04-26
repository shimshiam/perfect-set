/**
 * SessionLog.jsx — Scrollable list of completed rep events.
 * Renders the persisted session history and exports it as JSON.
 */
import './SessionLog.css';

export default function SessionLog({ entries, onResetSession, globalReps, globalAbortedReps = 0 }) {
  const formatTime = (ts) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const exportSession = () => {
    if (entries.length === 0) return;
    const payload = {
      summary: {
        completedReps: globalReps,
        abortedReps: globalAbortedReps,
        totalAttempts: globalReps + globalAbortedReps,
      },
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
      <div className="session-log__header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 className="session-log__title" style={{ margin: 0 }}>Session Log</h2>
        {entries.length > 0 && (
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              className="session-log__export-btn"
              onClick={exportSession}
              style={{ padding: '6px 12px', fontSize: '0.8rem', cursor: 'pointer', background: '#3b82f6', color: 'white', border: 'none', borderRadius: '4px', fontWeight: 'bold' }}
              title="Export session data to JSON"
            >
              Complete Set
            </button>
            <button
              className="session-log__export-btn"
              onClick={onResetSession}
              style={{ padding: '6px 12px', fontSize: '0.8rem', cursor: 'pointer', background: '#111827', color: 'white', border: '1px solid rgba(255,255,255,0.12)', borderRadius: '4px', fontWeight: 'bold' }}
              title="Clear the saved session from this browser"
            >
              New Session
            </button>
          </div>
        )}
      </div>
      {entries.length === 0 ? (
        <p className="session-log__empty">No reps recorded yet. Start your set!</p>
      ) : (
        <ul className="session-log__list">
          {entries.map((entry) => (
            <li key={`${entry.attempt}-${entry.timestamp}`} className="session-log__item">
              <span className="session-log__rep-number">Rep {entry.attempt}</span>
              <span className="session-log__time">{formatTime(entry.timestamp)}</span>
              <span className={`session-log__form-icon ${entry.perfectForm ? 'session-log__form-icon--good' : 'session-log__form-icon--bad'}`}>
                {entry.perfectForm ? 'OK' : 'X'}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
