import React from "react";

interface ApprovalPromptProps {
  step: string;
  onApprove: () => void;
  onEdit: () => void;
  onReject: () => void;
}

const ApprovalPrompt: React.FC<ApprovalPromptProps> = ({ step, onApprove, onEdit, onReject }) => (
  <div style={{ border: "2px solid #4f8cff", borderRadius: 6, padding: 12, margin: 8 }}>
    <div style={{ fontWeight: 600, marginBottom: 8 }}>Approve step: {step}?</div>
    <button onClick={onApprove} style={{ marginRight: 8 }}>Approve</button>
    <button onClick={onEdit} style={{ marginRight: 8 }}>Edit</button>
    <button onClick={onReject}>Reject</button>
  </div>
);

export default ApprovalPrompt; 