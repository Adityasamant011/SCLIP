import React from "react";
import { useRealtimeStore } from "../hooks/useRealtimeStore";

interface ProgressDisplayProps {
  percent?: number;
  status?: string;
  step?: string;
}

// If props are not provided, use real-time progress from the store
const ProgressDisplay: React.FC<ProgressDisplayProps> = (props) => {
  const storeProgress = useRealtimeStore((s) => s.progress);
  const percent = props.percent ?? storeProgress.percent;
  const status = props.status ?? storeProgress.status;
  const step = props.step ?? storeProgress.step;
  return (
    <div style={{ width: "100%", margin: "8px 0" }}>
      <div style={{ fontWeight: 500 }}>{step}</div>
      <div style={{ background: "#222", borderRadius: 4, height: 16, overflow: "hidden" }}>
        <div style={{ width: `${percent}%`, background: "#4f8cff", height: "100%" }} />
      </div>
      <div style={{ fontSize: 12, color: "#888" }}>{status}</div>
    </div>
  );
};

export default ProgressDisplay; 