import React from "react";
import { useRealtimeStore } from "../hooks/useRealtimeStore";

const blockColors: Record<string, string> = {
  video: "#4f8cff",
  audio: "#ffb84f",
  image: "#4fff8c",
  default: "#888"
};

const TimelinePanel: React.FC = () => {
  const files = useRealtimeStore((s) => s.files);
  const toolCalls = useRealtimeStore((s) => s.toolCalls);
  const toolResults = useRealtimeStore((s) => s.toolResults);

  // Filter clips (video, audio, image)
  const clips = files.filter(f => f.type && ["video", "audio", "image"].some(t => f.type.startsWith(t)));

  // Find effects/transitions from toolCalls/toolResults
  const effects = toolCalls.filter(c => c.tool === "video_processor" && c.message?.toLowerCase().includes("effect"));
  const transitions = toolCalls.filter(c => c.tool === "video_processor" && c.message?.toLowerCase().includes("transition"));

  if (clips.length === 0) {
    return <div style={{ padding: 16, color: "#888" }}>No timeline clips yet.</div>;
  }

  return (
    <div style={{ padding: 16 }}>
      <h3>Timeline</h3>
      <div style={{ display: "flex", alignItems: "center", gap: 8, overflowX: "auto", padding: 8, background: "#222", borderRadius: 8 }}>
        {clips.map((clip, idx) => {
          const color = blockColors[clip.type?.split("/")[0] || "default"] || blockColors.default;
          return (
            <div key={clip.path || clip.filename || idx} style={{
              minWidth: 100, maxWidth: 200, height: 40, background: color, borderRadius: 6, marginRight: 8, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", position: "relative"
            }}>
              <div style={{ fontWeight: 500, fontSize: 13 }}>{clip.filename || clip.name}</div>
              {clip.duration && <div style={{ fontSize: 11 }}>{clip.duration}s</div>}
              <div style={{ fontSize: 10, color: "#222", position: "absolute", bottom: 2, right: 6 }}>{clip.type}</div>
            </div>
          );
        })}
        {/* Effects and transitions as markers */}
        {effects.map((eff, idx) => (
          <div key={"effect" + idx} style={{ color: "#fff", background: "#a0f", borderRadius: 4, padding: "2px 6px", marginLeft: 4, fontSize: 12 }}>Effect</div>
        ))}
        {transitions.map((tr, idx) => (
          <div key={"transition" + idx} style={{ color: "#fff", background: "#0af", borderRadius: 4, padding: "2px 6px", marginLeft: 4, fontSize: 12 }}>Transition</div>
        ))}
      </div>
    </div>
  );
};

export default TimelinePanel; 