/**
 * App.jsx - Root component for Perfect Set.
 * Orchestrates webcam capture, WebSocket streaming, persisted session state,
 * exercise selection, and UI rendering.
 */
import { useState, useCallback, useEffect } from 'react';
import useWebcam from './hooks/useWebcam.js';
import useWebSocket from './hooks/useWebSocket.js';
import VideoFeed from './components/VideoFeed.jsx';
import Dashboard from './components/Dashboard.jsx';
import SessionLog from './components/SessionLog.jsx';
import { initAudio } from './utils/audio.js';
import {
  EXERCISES,
  appendRepEvent,
  createEmptySession,
  getExerciseTotals,
  loadSession,
  saveSession,
  setActiveExercise,
} from './utils/sessionStorage.js';
import './App.css';

export default function App() {
  const { videoRef, captureFrame, isReady, error: camError } = useWebcam();
  const [session, setSession] = useState(() => loadSession());
  const [audioEnabled, setAudioEnabled] = useState(false);

  const activeExercise = session.activeExercise;

  useEffect(() => {
    saveSession(session);
  }, [session]);

  const handleExerciseChange = useCallback((exercise) => {
    setSession((prev) => setActiveExercise(prev, exercise));
  }, []);

  const handleRepCompleted = useCallback((event) => {
    const exercise = event.exercise ?? activeExercise;
    setSession((prev) => appendRepEvent(prev, exercise, 'completed', event));
  }, [activeExercise]);

  const handleRepAborted = useCallback((event) => {
    const exercise = event.exercise ?? activeExercise;
    setSession((prev) => appendRepEvent(prev, exercise, 'aborted', event));
  }, [activeExercise]);

  const {
    isConnected,
    isReconnecting,
    latestStatus,
    sendFrame,
    canSendFrame,
    error: wsError,
  } = useWebSocket(activeExercise, handleRepCompleted, handleRepAborted);

  const handleEnableAudio = useCallback(() => {
    initAudio();
    setAudioEnabled(true);
  }, []);

  const handleResetSession = useCallback(() => {
    setSession(createEmptySession(activeExercise));
  }, [activeExercise]);

  const landmarks = latestStatus?.landmarks ?? null;
  const totals = getExerciseTotals(session, activeExercise);

  return (
    <div className="app">
      <header className="app__header">
        <div>
          <h1 className="app__title">
            <span className="app__title-accent">Perfect</span> Set
          </h1>
          <p className="app__subtitle">Real-Time Physical Form Tracker</p>
        </div>

        <div className="app__controls" aria-label="Workout controls">
          <div className="app__exercise-selector" aria-label="Exercise selector">
            {Object.entries(EXERCISES).map(([key, label]) => (
              <button
                key={key}
                type="button"
                className={`app__exercise-button ${activeExercise === key ? 'app__exercise-button--active' : ''}`}
                onClick={() => handleExerciseChange(key)}
              >
                {label}
              </button>
            ))}
          </div>

          {!audioEnabled && (
            <button
              type="button"
              className="app__audio-button"
              onClick={handleEnableAudio}
            >
              Enable Voice Coaching
            </button>
          )}
        </div>
      </header>

      {camError && (
        <div className="app__error" role="alert">{camError}</div>
      )}
      {wsError && (
        <div className="app__error" role="alert">{wsError}</div>
      )}

      <main className="app__main">
        <VideoFeed
          videoRef={videoRef}
          captureFrame={captureFrame}
          isReady={isReady}
          sendFrame={sendFrame}
          canSendFrame={canSendFrame}
          isConnected={isConnected}
          landmarks={landmarks}
        />

        <div className="app__sidebar">
          <Dashboard
            status={latestStatus}
            exercise={activeExercise}
            globalReps={totals.completedReps}
            isConnected={isConnected}
            isReconnecting={isReconnecting}
            audioEnabled={audioEnabled}
          />
          <SessionLog
            session={session}
            activeExercise={activeExercise}
            onResetSession={handleResetSession}
          />
        </div>
      </main>
    </div>
  );
}
