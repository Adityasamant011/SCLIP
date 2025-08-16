import React from "react";

interface ToolCallDisplayProps {
  tool: string;
  step: string;
  message: string;
}

const ToolCallDisplay: React.FC<ToolCallDisplayProps> = ({ tool, step, message }) => (
  <div style={{ border: "1px solid #333", borderRadius: 4, padding: 8, margin: 4 }}>
    <div><strong>Tool:</strong> {tool}</div>
    <div><strong>Step:</strong> {step}</div>
    <div><strong>Message:</strong> {message}</div>
  </div>
);

export default ToolCallDisplay; 