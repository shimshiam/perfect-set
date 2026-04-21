/**
 * SessionLog.jsx — Scrollable list of completed rep events.
 * Each time rep_count increments, a new entry is pushed.
 */
import { useState, useEffect, useRef } from 'react';
import './SessionLog.css';

export default function SessionLog({ status, globalReps, globalAbortedReps = 0 }) {
  const [reps, setReps] = useState([]);
  const prevGlobalReps = useRef(0);
  const prevGlobalAbortedReps = useRef(0);
  const listRef = useRef(null);

  useEffect(() => {
    let newEntries = [];
    const totalAttempts = globalReps + globalAbortedReps;

    if (globalReps > prevGlobalReps.current) {
      newEntries.push({
        rep: totalAttempts,
        timestamp: Date.now(),
        perfectForm: true,
      });
      prevGlobalReps.current = globalReps;
    }

    if (globalAbortedReps > prevGlobalAbortedReps.current) {
      newEntries.push({
        rep: totalAttempts,
        timestamp: Date.now(),
        perfectForm: false,
      });
      prevGlobalAbortedReps.current = globalAbortedReps;
    }

    if (newEntries.length > 0) {
      setReps((prev) => [...newEntries, ...prev]);
    }
  }, [globalReps, globalAbortedReps]);

  const formatTime = (ts) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const exportSession = () => {
    if (reps.length === 0) return;
    const blob = new Blob([JSON.stringify(reps, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const dlAnchorElem = document.createElement('a');
    dlAnchorElem.setAttribute("href", url);
    dlAnchorElem.setAttribute("download", `perfect-set-session-${Date.now()}.json`);
    document.body.appendChild(dlAnchorElem);
    dlAnchorElem.click();
    document.body.removeChild(dlAnchorElem);
    URL.revokeObjectURL(url);
  };

  return (
    <section className="session-log" aria-label="Session rep history">
      <div className="session-log__header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 className="session-log__title" style={{ margin: 0 }}>Session Log</h2>
        {reps.length > 0 && (
          <button 
            className="session-log__export-btn" 
            onClick={exportSession} 
            style={{ padding: '6px 12px', fontSize: '0.8rem', cursor: 'pointer', background: '#3b82f6', color: 'white', border: 'none', borderRadius: '4px', fontWeight: 'bold' }}
            title="Export session data to JSON"
          >
            Complete Set
          </button>
        )}
      </div>
      {reps.length === 0 ? (
        <p className="session-log__empty">No reps recorded yet. Start your set!</p>
      ) : (
        <ul ref={listRef} className="session-log__list">
          {reps.map((entry, i) => (
            <li key={`${entry.rep}-${entry.timestamp}`} className="session-log__item">
              <span className="session-log__rep-number">Rep {entry.rep}</span>
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
