import React from "react";
import { useRealtimeStore } from "../hooks/useRealtimeStore";
import { approveStep } from "../utils/api";

const ApprovalPanel: React.FC = () => {
  // Find the latest approval request (user_input_request)
  const approvalRequest = useRealtimeStore((s) =>
    [...s.messages].reverse().find((msg) => msg.type === "user_input_request")
  );
  const sessionId = useRealtimeStore((s) => {
    // Try to get session_id from the latest message
    const last = [...s.messages].reverse().find((m) => m.session_id);
    return last?.session_id || "";
  });

  if (!approvalRequest) {
    return <div style={{ padding: 16, color: "#888" }}>No approval needed at this time.</div>;
  }

  async function handleAction(action: "approve" | "edit" | "reject") {
    if (!sessionId) return;
    await approveStep(sessionId, {
      step: approvalRequest.step_id || approvalRequest.step || "",
      action,
      modifications: {},
    });
    // Optionally: update the store or show a confirmation
    alert(`Action sent: ${action}`);
  }

  return (
    <div style={{ padding: 16, border: "2px solid #4f8cff", borderRadius: 8, margin: 8 }}>
      <div style={{ fontWeight: 600, marginBottom: 8 }}>
        Approval needed: {approvalRequest.step_id || approvalRequest.step}
      </div>
      <div style={{ marginBottom: 8 }}>{approvalRequest.question || approvalRequest.message || "Approve this step?"}</div>
      <button onClick={() => handleAction("approve")} style={{ marginRight: 8 }}>Approve</button>
      <button onClick={() => handleAction("edit")} style={{ marginRight: 8 }}>Edit</button>
      <button onClick={() => handleAction("reject")}>Reject</button>
    </div>
  );
};

export default ApprovalPanel; 