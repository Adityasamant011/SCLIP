import React from "react";
import { useRealtimeStore } from "../hooks/useRealtimeStore";

const ToolCallResultPanel: React.FC = () => {
  const toolCalls = useRealtimeStore((s) => s.toolCalls);
  const toolResults = useRealtimeStore((s) => s.toolResults);

  if ((!toolCalls || toolCalls.length === 0) && (!toolResults || toolResults.length === 0)) {
    return <div style={{ padding: 16, color: "#888" }}>No tool calls or results yet.</div>;
  }

  // Try to match results to calls by step/tool
  const items = toolCalls.map((call) => {
    const result = toolResults.find(
      (res) => res.tool === call.tool && res.step === call.step
    );
    return { call, result };
  });

  return (
    <div style={{ padding: 16 }}>
      <h3>Tool Calls & Results</h3>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {items.map(({ call, result }, idx) => (
          <div key={call.step + call.tool + idx} style={{ border: "1px solid #333", borderRadius: 6, padding: 8 }}>
            <div><strong>Tool:</strong> {call.tool}</div>
            <div><strong>Step:</strong> {call.step}</div>
            <div><strong>Call:</strong> {call.message}</div>
            {result ? (
              <div style={{ marginTop: 8 }}>
                <strong>Result:</strong> {result.message}
                {result.result && (
                  <pre style={{ background: "#181818", color: "#fff", padding: 8, borderRadius: 4, marginTop: 4 }}>
                    {JSON.stringify(result.result, null, 2)}
                  </pre>
                )}
              </div>
            ) : (
              <div style={{ color: "#aaa", marginTop: 8 }}>No result yet.</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default ToolCallResultPanel; 