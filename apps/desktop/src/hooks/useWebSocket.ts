import { useEffect, useRef, useState, useCallback } from "react";
import { useRealtimeStore } from "./useRealtimeStore";

export type WebSocketMessage = any;

interface UseWebSocketOptions {
  sessionId: string;
  onMessage?: (msg: WebSocketMessage) => void;
  url?: string;
}

export function useWebSocket({ sessionId, onMessage, url }: UseWebSocketOptions) {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<number | null>(null);
  const sessionIdRef = useRef<string>(sessionId);
  const onMessageRef = useRef(onMessage);
  
  // Update refs when props change
  sessionIdRef.current = sessionId;
  onMessageRef.current = onMessage;
  
  // Zustand store actions
  const { handleMessage, setConnectionStatus, setError } = useRealtimeStore.getState();

  const wsUrl = url || (sessionId ? `ws://localhost:8001/api/stream/${sessionId}` : "");

  const connect = useCallback(() => {
    if (!sessionIdRef.current) return; // Do not connect if sessionId is missing
    
    // Don't reconnect if already connected
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return;
    }
    
    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    
    ws.onopen = () => {
      setConnected(true);
      setConnectionStatus("connected");
      console.log("WebSocket connected successfully");
    };
    
    ws.onclose = (event) => {
      setConnected(false);
      setConnectionStatus("disconnected");
      console.log("WebSocket closed:", event.code, event.reason);
      
      // Only reconnect if it wasn't a normal closure and we still have a sessionId
      if (event.code !== 1000 && sessionIdRef.current) {
        setConnectionStatus("reconnecting");
        reconnectRef.current = window.setTimeout(connect, 2000);
      }
    };
    
    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      setError("WebSocket error");
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleMessage(data); // Always dispatch to store
        if (onMessageRef.current) onMessageRef.current(data); // Optional legacy callback
      } catch (e) {
        console.error("Failed to parse WebSocket message:", e);
        setError("Failed to parse WebSocket message");
      }
    };
  }, [wsUrl, handleMessage, setConnectionStatus, setError]);

  useEffect(() => {
    if (!sessionId) {
      // Clean up if no sessionId
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (reconnectRef.current) {
        window.clearTimeout(reconnectRef.current);
        reconnectRef.current = null;
      }
      setConnected(false);
      setConnectionStatus("disconnected");
      return;
    }
    
    connect();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (reconnectRef.current) {
        window.clearTimeout(reconnectRef.current);
        reconnectRef.current = null;
      }
    };
  }, [sessionId, connect]);

  const sendMessage = useCallback((msg: any) => {
    if (wsRef.current && connected) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, [connected]);

  return { connected, sendMessage };
} 