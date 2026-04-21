/**
 * App.jsx — Root component for Perfect Set.
 * Orchestrates webcam capture, WebSocket streaming, and UI rendering.
 */
import { useState, useCallback } from 'react';
import useWebcam from './hooks/useWebcam.js';
import useWebSocket from './hooks/useWebSocket.js';
import VideoFeed from './components/VideoFeed.jsx';
import Dashboard from './components/Dashboard.jsx';
import SessionLog from './components/SessionLog.jsx';
import { initAudio } from './utils/audio.js';
import './App.css';

export default function App() {
  const { videoRef, captureFrame, isReady, error: camError } = useWebcam();
  
  const [globalReps, setGlobalReps] = useState(0);
  const [globalAbortedReps, setGlobalAbortedReps] = useState(0);

  const handleRepCompleted = useCallback(() => {
    setGlobalReps((prev) => prev + 1);
  }, []);

  const handleRepAborted = useCallback(() => {
    setGlobalAbortedReps((prev) => prev + 1);
  }, []);

  const { isConnected, isReconnecting, latestStatus, sendFrame, error: wsError } = useWebSocket(handleRepCompleted, handleRepAborted);

  const [audioEnabled, setAudioEnabled] = useState(false);
  const handleEnableAudio = useCallback(() => {
    initAudio();
    setAudioEnabled(true);
  }, []);

  const landmarks = latestStatus?.landmarks ?? null;

  return (
    <div className="app">
      <header className="app__header">
        <h1 className="app__title">
          <span className="app__title-accent">Perfect</span> Set
        </h1>
        <p className="app__subtitle">Real-Time Physical Form Tracker</p>
        {!audioEnabled && (
          <button 
            onClick={handleEnableAudio} 
            style={{marginTop: '12px', padding: '10px 20px', background: '#00ff88', color: '#111', border: 'none', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer', fontSize: '1rem', boxShadow: '0 0 10px rgba(0,255,136,0.3)'}}
          >
            🔊 Click to Enable Voice Coaching
          </button>
        )}
      </header>

      {/* Error banners */}
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
          isConnected={isConnected}
          landmarks={landmarks}
        />

        <div className="app__sidebar">
          <Dashboard
            status={latestStatus}
            globalReps={globalReps}
            isConnected={isConnected}
            isReconnecting={isReconnecting}
          />
          <SessionLog status={latestStatus} globalReps={globalReps} globalAbortedReps={globalAbortedReps} />
        </div>
      </main>
    </div>
  );
}
