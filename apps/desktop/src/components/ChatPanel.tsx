import React from "react";
import { useRealtimeStore } from "../hooks/useRealtimeStore";

const ChatPanel: React.FC = () => {
  const messages = useRealtimeStore((s) => s.messages);

  if (!messages || messages.length === 0) {
    return <div style={{ padding: 16, color: "#888" }}>No messages yet.</div>;
  }

  return (
    <div style={{ padding: 16, maxHeight: 400, overflowY: "auto", background: "#181818", borderRadius: 8 }}>
      <h3>Interaction Panel</h3>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {messages.map((msg, idx) => {
          let style: React.CSSProperties = { padding: 8, borderRadius: 4 };
          if (msg.type === "error") style = { ...style, background: "#ffdddd", color: "#a00" };
          else if (msg.type === "progress") style = { ...style, background: "#222", color: "#4f8cff" };
          else if (msg.type === "ai_message") style = { ...style, background: "#222", color: "#fff" };
          else style = { ...style, background: "#222", color: "#aaa" };
          return (
            <div key={msg.timestamp || idx} style={style}>
              <div style={{ fontSize: 11, opacity: 0.7 }}>{msg.type} {msg.timestamp && `| ${msg.timestamp}`}</div>
              <div style={{ fontWeight: 500 }}>{msg.content || msg.message || msg.detail || JSON.stringify(msg)}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ChatPanel; 