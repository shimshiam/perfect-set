/**
 * useWebcam.js — Custom hook for accessing the user's webcam.
 * Returns a video ref to attach to a <video> element, an async captureFrame()
 * function that returns a JPEG Blob, and an error state.
 */
import { useRef, useState, useEffect, useCallback } from 'react';

const VIDEO_CONSTRAINTS = {
  video: { width: 640, height: 480, facingMode: 'user' },
  audio: false,
};
const MAX_CAPTURE_WIDTH = 512;
const JPEG_QUALITY = 0.6;

export default function useWebcam() {
  const videoRef = useRef(null);
  const canvasRef = useRef(document.createElement('canvas'));
  const streamRef = useRef(null);
  const [error, setError] = useState(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function startCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia(VIDEO_CONSTRAINTS);
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.onloadedmetadata = () => {
            if (!cancelled) setIsReady(true);
          };
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err.name === 'NotAllowedError'
              ? 'Camera permission denied. Please allow access and reload.'
              : `Camera error: ${err.message}`
          );
        }
      }
    }

    startCamera();

    return () => {
      cancelled = true;
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      }
    };
  }, []);

  const captureFrame = useCallback(() => {
    const video = videoRef.current;
    if (!video || video.readyState < 2) return Promise.resolve(null);

    const sourceWidth = video.videoWidth;
    const sourceHeight = video.videoHeight;
    const captureWidth = Math.min(sourceWidth, MAX_CAPTURE_WIDTH);
    const captureHeight = Math.round((sourceHeight * captureWidth) / sourceWidth);

    const canvas = canvasRef.current;
    if (canvas.width !== captureWidth || canvas.height !== captureHeight) {
      canvas.width = captureWidth;
      canvas.height = captureHeight;
    }

    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, captureWidth, captureHeight);

    return new Promise((resolve) => {
      canvas.toBlob(resolve, 'image/jpeg', JPEG_QUALITY);
    });
  }, []);

  return { videoRef, captureFrame, isReady, error };
}
