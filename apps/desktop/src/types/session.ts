export interface Session {
  session_id: string;
  user_prompt: string;
  current_step: string;
  tool_outputs: Record<string, any>;
  user_approvals: Array<any>;
  retry_counts: Record<string, number>;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface SessionInfo {
  session_id: string;
  status: string;
  current_step: string;
  progress: number;
  created_at: string;
  updated_at: string;
} 