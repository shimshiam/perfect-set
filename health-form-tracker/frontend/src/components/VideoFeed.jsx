/**
 * VideoFeed.jsx — Webcam video display with skeleton canvas overlay.
 * Captures frames at ~15 FPS and sends them to the backend.
 */
import { useRef, useEffect } from 'react';
import { drawSkeleton } from '../utils/drawing.js';
import './VideoFeed.css';

const FRAME_INTERVAL_MS = 66;

export default function VideoFeed({
  videoRef,
  captureFrame,
  isReady,
  sendFrame,
  canSendFrame,
  isConnected,
  landmarks,
}) {
  const canvasRef = useRef(null);
  const landmarksRef = useRef(landmarks);
  const canvasSizeRef = useRef({ width: 0, height: 0 });
  const captureInProgressRef = useRef(false);
  const lastCaptureAtRef = useRef(0);

  useEffect(() => {
    landmarksRef.current = landmarks;
  }, [landmarks]);

  // Frame capture loop — throttled to ~15 FPS and gated on backend capacity.
  useEffect(() => {
    if (!isReady || !isConnected) return;

    let cancelled = false;
    let animId;

    const tick = (now) => {
      if (
        !cancelled &&
        !captureInProgressRef.current &&
        now - lastCaptureAtRef.current >= FRAME_INTERVAL_MS &&
        canSendFrame()
      ) {
        captureInProgressRef.current = true;
        lastCaptureAtRef.current = now;
        void captureFrame()
          .then((frame) => {
            if (!cancelled && frame) {
              sendFrame(frame);
            }
          })
          .finally(() => {
            captureInProgressRef.current = false;
          });
      }

      if (!cancelled) {
        animId = requestAnimationFrame(tick);
      }
    };

    animId = requestAnimationFrame(tick);

    return () => {
      cancelled = true;
      cancelAnimationFrame(animId);
      captureInProgressRef.current = false;
    };
  }, [isReady, isConnected, canSendFrame, captureFrame, sendFrame]);

  // Skeleton drawing loop
  useEffect(() => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;

    let animId;
    let ctx = canvas.getContext('2d');

    const draw = () => {
      if (video.videoWidth && video.videoHeight) {
        if (
          canvasSizeRef.current.width !== video.videoWidth ||
          canvasSizeRef.current.height !== video.videoHeight
        ) {
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          canvasSizeRef.current = { width: canvas.width, height: canvas.height };
          ctx = canvas.getContext('2d');
        }

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
