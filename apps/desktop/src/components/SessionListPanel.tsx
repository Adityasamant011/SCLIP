import React, { useEffect, useState } from "react";
import { listSessions } from "../utils/api";
import { formatDate } from "../utils/helpers";

interface SessionInfo {
  session_id: string;
  status: string;
  current_step: string;
  progress: number;
  created_at: string;
  updated_at: string;
}

const SessionListPanel: React.FC<{ currentSessionId?: string; onSwitch?: (id: string) => void }> = ({ currentSessionId, onSwitch }) => {
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchSessions() {
      setLoading(true);
      setError(null);
      try {
        const resp = await listSessions();
        setSessions(resp.sessions || []);
      } catch (e: any) {
        setError(e.message || "Failed to load sessions");
      } finally {
        setLoading(false);
      }
    }
    fetchSessions();
  }, []);

  async function handleDelete(id: string) {
    // TODO: Call backend to delete session
    setSessions((prev) => prev.filter((s) => s.session_id !== id));
    alert("Session deleted (stub)");
  }

  async function handleReplay(id: string) {
    // TODO: Implement replay logic
    alert("Replay session: " + id);
  }

  return (
    <div style={{ padding: 16 }} aria-label="Session List Panel">
      <h3>Sessions</h3>
      {loading && <div>Loading...</div>}
      {error && <div style={{ color: "#a00" }}>{error}</div>}
      <ul style={{ listStyle: "none", padding: 0 }}>
        {sessions.map((s) => (
          <li key={s.session_id} style={{
            background: s.session_id === currentSessionId ? "#4f8cff22" : undefined,
            borderRadius: 6, marginBottom: 8, padding: 8, display: "flex", alignItems: "center"
          }}>
            <button
              onClick={() => onSwitch && onSwitch(s.session_id)}
              style={{ fontWeight: s.session_id === currentSessionId ? 700 : 400, marginRight: 12 }}
              aria-label={`Switch to session ${s.session_id}`}
            >
              {s.session_id.slice(0, 8)}
            </button>
            <span style={{ fontSize: 12, color: "#888", marginRight: 8 }}>{s.status}</span>
            <span style={{ fontSize: 12, color: "#888", marginRight: 8 }}>{formatDate(s.updated_at)}</span>
            <button onClick={() => handleReplay(s.session_id)} aria-label={`Replay session ${s.session_id}`} style={{ marginRight: 8 }}>Replay</button>
            <button onClick={() => handleDelete(s.session_id)} aria-label={`Delete session ${s.session_id}`}>Delete</button>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default SessionListPanel; 