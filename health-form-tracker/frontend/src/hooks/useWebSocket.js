/**
 * useWebSocket.js — Custom hook for managing the WebSocket connection
 * to the Perfect Set backend. Handles reconnection logic and exposes
 * the latest server status.
 */
import { useRef, useState, useEffect, useCallback } from 'react';

const WS_URL = 'ws://localhost:8000/ws/pushups';
const RECONNECT_DELAY_MS = 3000;
const MAX_RECONNECT_ATTEMPTS = 5;

export default function useWebSocket(onRepCompleted) {
  const wsRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef(null);
  const mountedRef = useRef(true);

  const [isConnected, setIsConnected] = useState(false);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [latestStatus, setLatestStatus] = useState(null);
  const [error, setError] = useState(null);

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
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const data = JSON.parse(event.data);
          if (data.type === "REP_COMPLETED") {
            if (onRepCompleted) onRepCompleted();
          } else if (data.type === "STATUS" || !data.error) {
            setLatestStatus(data);
          }
        } catch {
          // Ignore malformed messages
        }
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        setIsConnected(false);
        wsRef.current = null;
        attemptReconnect();
      };

      ws.onerror = () => {
        // onclose will fire after onerror — reconnection handled there
      };
    } catch {
      attemptReconnect();
    }
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
      if (mountedRef.current) connect();
    }, RECONNECT_DELAY_MS);
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

  const sendFrame = useCallback((base64Frame) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ frame: base64Frame }));
    }
  }, []);

  return { isConnected, isReconnecting, latestStatus, sendFrame, error };
}
