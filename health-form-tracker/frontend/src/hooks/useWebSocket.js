/**
 * useWebSocket.js — Custom hook for managing the WebSocket connection
 * to the Perfect Set backend. Handles reconnection logic and exposes
 * the latest server status.
 */
import { useRef, useState, useEffect, useCallback } from 'react';

const WS_URL = 'ws://localhost:8000/ws/pushups';
const RECONNECT_DELAY_MS = 3000;
const MAX_RECONNECT_ATTEMPTS = 5;

export default function useWebSocket(onRepCompleted, onRepAborted) {
  const wsRef = useRef(null);
  const connectRef = useRef(() => {});
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef(null);
  const mountedRef = useRef(true);
  const frameInFlightRef = useRef(false);
  const queuedFrameRef = useRef(null);

  const [isConnected, setIsConnected] = useState(false);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [latestStatus, setLatestStatus] = useState(null);
  const [error, setError] = useState(null);

  const flushQueuedFrame = useCallback(() => {
    const ws = wsRef.current;
    const queuedFrame = queuedFrameRef.current;

    if (!ws || ws.readyState !== WebSocket.OPEN || !queuedFrame) {
      return false;
    }

    queuedFrameRef.current = null;
    frameInFlightRef.current = true;
    ws.send(queuedFrame);
    return true;
  }, []);

  const releaseFrameSlot = useCallback(() => {
    frameInFlightRef.current = false;
    flushQueuedFrame();
  }, [flushQueuedFrame]);

  const resetFrameQueue = useCallback(() => {
    frameInFlightRef.current = false;
    queuedFrameRef.current = null;
  }, []);

  const attemptReconnect = useCallback(() => {
    if (!mountedRef.current) return;
    if (reconnectAttempts.current >= MAX_RECONNECT_ATTEMPTS) {
      setError('Unable to connect to server. Please ensure the backend is running.');
      setIsReconnecting(false);
      return;
    }

    setIsReconnecting(true);
    reconnectAttempts.current += 1;

    reconnectTimer.current = setTimeout(() => {
      if (mountedRef.current) connectRef.current();
    }, RECONNECT_DELAY_MS);
  }, []);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;

    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        setIsConnected(true);
        setIsReconnecting(false);
        setError(null);
        reconnectAttempts.current = 0;
        resetFrameQueue();
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'STATUS') {
            setLatestStatus(data);
            setError(null);
            releaseFrameSlot();
            return;
          }

          if (data.type === "REP_COMPLETED") {
            if (onRepCompleted) onRepCompleted();
            return;
          }

          if (data.type === "REP_ABORTED") {
            if (onRepAborted) onRepAborted();
            return;
          }

          if (data.error) {
            setError(data.error);
            releaseFrameSlot();
          }
        } catch {
          // Ignore malformed messages
        }
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        setIsConnected(false);
        wsRef.current = null;
        resetFrameQueue();
        attemptReconnect();
      };

      ws.onerror = () => {
        // onclose will fire after onerror — reconnection handled there
      };
    } catch {
      resetFrameQueue();
      attemptReconnect();
    }
  }, [attemptReconnect, onRepAborted, onRepCompleted, releaseFrameSlot, resetFrameQueue]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      clearTimeout(reconnectTimer.current);
      if (wsRef.current) {
        wsRef.current.onclose = null; // Prevent reconnect on intentional close
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  const canSendFrame = useCallback(() => {
    const ws = wsRef.current;
    return Boolean(ws && ws.readyState === WebSocket.OPEN && !frameInFlightRef.current);
  }, []);

  const sendFrame = useCallback((frameBlob) => {
    const ws = wsRef.current;

    if (!ws || ws.readyState !== WebSocket.OPEN || !frameBlob) {
      return false;
    }

    if (frameInFlightRef.current) {
      queuedFrameRef.current = frameBlob;
      return false;
    }

    frameInFlightRef.current = true;
    ws.send(frameBlob);
    return true;
  }, []);

  return { isConnected, isReconnecting, latestStatus, sendFrame, canSendFrame, error };
}
