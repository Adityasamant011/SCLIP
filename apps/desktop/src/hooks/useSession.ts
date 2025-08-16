import { useState } from "react";
import { Session, SessionInfo } from "../types/session";
import { BackendMessage } from "../types/messages";
import { submitPrompt, approveStep, listSessions, listSessionFiles } from "../utils/api";

// TODO: Replace with Zustand or Redux if desired
export function useSession() {
  const [session, setSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<BackendMessage[]>([]);
  const [files, setFiles] = useState<any[]>([]);

  // Start a new session
  async function startSession(promptData: any) {
    const resp = await submitPrompt(promptData);
    setSession({ ...resp });
    setMessages([]);
    setFiles([]);
    return resp;
  }

  // Approve a step
  async function approve(step: any) {
    if (!session) return;
    return approveStep(session.session_id, step);
  }

  // Add a message
  function addMessage(msg: BackendMessage) {
    setMessages((prev) => [...prev, msg]);
  }

  // Update files
  async function refreshFiles() {
    if (!session) return;
    const resp = await listSessionFiles(session.session_id);
    setFiles(resp.files || []);
  }

  return {
    session,
    messages,
    files,
    startSession,
    approve,
    addMessage,
    refreshFiles,
    setSession,
  };
} 