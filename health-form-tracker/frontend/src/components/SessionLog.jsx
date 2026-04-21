/**
 * SessionLog.jsx — Scrollable list of completed rep events.
 * Each time rep_count increments, a new entry is pushed.
 */
import { useState, useEffect, useRef } from 'react';
import './SessionLog.css';

export default function SessionLog({ status }) {
  const [reps, setReps] = useState([]);
  const prevRepCount = useRef(0);
  const listRef = useRef(null);

  useEffect(() => {
    if (!status) return;
    if (status.rep_count > prevRepCount.current) {
      setReps((prev) => [
        {
          rep: status.rep_count,
          timestamp: Date.now(),
          perfectForm: status.perfect_form,
        },
        ...prev,
      ]);
    }
    prevRepCount.current = status.rep_count;
  }, [status?.rep_count]);

  const formatTime = (ts) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  return (
    <section className="session-log" aria-label="Session rep history">
      <h2 className="session-log__title">Session Log</h2>
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
