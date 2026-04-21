/**
 * App.jsx — Root component for Perfect Set.
 * Orchestrates webcam capture, WebSocket streaming, and UI rendering.
 */
import useWebcam from './hooks/useWebcam.js';
import useWebSocket from './hooks/useWebSocket.js';
import VideoFeed from './components/VideoFeed.jsx';
import Dashboard from './components/Dashboard.jsx';
import SessionLog from './components/SessionLog.jsx';
import './App.css';

export default function App() {
  const { videoRef, captureFrame, isReady, error: camError } = useWebcam();
  const { isConnected, isReconnecting, latestStatus, sendFrame, error: wsError } = useWebSocket();

  const landmarks = latestStatus?.landmarks ?? null;

  return (
    <div className="app">
      <header className="app__header">
        <h1 className="app__title">
          <span className="app__title-accent">Perfect</span> Set
        </h1>
        <p className="app__subtitle">Real-Time Physical Form Tracker</p>
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
            isConnected={isConnected}
            isReconnecting={isReconnecting}
          />
          <SessionLog status={latestStatus} />
        </div>
      </main>
    </div>
  );
}
