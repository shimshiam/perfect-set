/**
 * VideoFeed.jsx — Webcam video display with skeleton canvas overlay.
 * Captures frames at ~15 FPS and sends them to the backend.
 */
import { useRef, useEffect } from 'react';
import { drawSkeleton } from '../utils/drawing.js';
import './VideoFeed.css';

export default function VideoFeed({ videoRef, captureFrame, isReady, sendFrame, isConnected, landmarks }) {
  const canvasRef = useRef(null);
  const intervalRef = useRef(null);
  const landmarksRef = useRef(landmarks);

  useEffect(() => {
    landmarksRef.current = landmarks;
  }, [landmarks]);

  // Frame capture loop — throttled to ~15 FPS
  useEffect(() => {
    if (!isReady || !isConnected) return;

    intervalRef.current = setInterval(() => {
      const frame = captureFrame();
      if (frame) sendFrame(frame);
    }, 66); // ~15 FPS

    return () => clearInterval(intervalRef.current);
  }, [isReady, isConnected, captureFrame, sendFrame]);

  // Skeleton drawing loop
  useEffect(() => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;

    let animId;
    const draw = () => {
      if (video.videoWidth && video.videoHeight) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        drawSkeleton(ctx, landmarksRef.current, canvas.width, canvas.height);
      }
      animId = requestAnimationFrame(draw);
    };

    draw();
    return () => cancelAnimationFrame(animId);
  }, [videoRef]);

  return (
    <section className="video-feed" aria-label="Webcam feed with pose overlay">
      <div className="video-feed__container">
        <video
          ref={videoRef}
          className="video-feed__video"
          autoPlay
          playsInline
          muted
        />
        <canvas ref={canvasRef} className="video-feed__canvas" />
        {!isReady && (
          <div className="video-feed__loading">
            <span className="video-feed__loading-text">Starting camera...</span>
          </div>
        )}
      </div>
    </section>
  );
}
