// Message types from backend - fluid and adaptive
export type MessageType =
  | "ai_message"
  | "tool_call"
  | "tool_result"
  | "progress"
  | "user_input_request"
  | "approval_received"
  | "error"
  | "connection_established"
  | "process_paused"
  | "workflow_complete"
  | "user_message"
  | "informational"
  | "interactive"
  | "adaptive"
  | "context_update"
  | "thinking"
  | "gui_update"
  // New agentic message types
  | "reasoning"
  | "tool_execution_start"
  | "tool_execution_complete"
  | "tool_progress"
  | "decision_context"
  | "decision_option"
  | "decision_made";

export interface BaseMessage {
  type: MessageType;
  session_id?: string;
  timestamp?: string;
  [key: string]: any;
}

export interface AiMessage extends BaseMessage {
  type: "ai_message";
  content: string;
}

export interface ToolCallMessage extends BaseMessage {
  type: "tool_call";
  tool: string;
  step: string;
  message: string;
}

export interface ToolResultMessage extends BaseMessage {
  type: "tool_result";
  tool: string;
  step: string;
  result: any;
  message: string;
}

export interface ProgressMessage extends BaseMessage {
  type: "progress";
  step: string;
  percent?: number;
  status?: string;
  description?: string;
}

export interface ErrorMessage extends BaseMessage {
  type: "error";
  detail: string;
}

// New agentic message interfaces
export interface ThinkingMessage extends BaseMessage {
  type: "thinking";
  content: string;
}

export interface ReasoningMessage extends BaseMessage {
  type: "reasoning";
  content: string;
  step_number?: number;
  total_steps?: number;
}

export interface ToolExecutionMessage extends BaseMessage {
  type: "tool_execution_start" | "tool_execution_complete";
  tool: string;
  description?: string;
  args?: any;
}

export interface ToolProgressMessage extends BaseMessage {
  type: "tool_progress";
  tool: string;
  status: string;
  progress: number;
}

export interface DecisionContextMessage extends BaseMessage {
  type: "decision_context";
  context: any;
  content?: string;
}

export interface DecisionOptionMessage extends BaseMessage {
  type: "decision_option";
  option: string;
  option_number?: number;
  total_options?: number;
  content?: string;
}

export interface DecisionMadeMessage extends BaseMessage {
  type: "decision_made";
  decision: string;
  reasoning?: string;
  content?: string;
}

// Add more message types as needed

export type BackendMessage =
  | AiMessage
  | ToolCallMessage
  | ToolResultMessage
  | ProgressMessage
  | ErrorMessage
  | ThinkingMessage
  | ReasoningMessage
  | ToolExecutionMessage
  | ToolProgressMessage
  | DecisionContextMessage
  | DecisionOptionMessage
  | DecisionMadeMessage
  | BaseMessage; 