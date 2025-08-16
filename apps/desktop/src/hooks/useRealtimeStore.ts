import { create } from 'zustand';
import { MessageType } from '../types/messages';

export interface Message {
  type: MessageType;
  content?: string;
  message?: string;
  detail?: string;
  session_id?: string;
  timestamp?: string;
  message_id?: string;
  tool?: string;
  args?: any;
  step?: string;
  description?: string;
  result?: any;
  success?: boolean;
  error?: string;
  percent?: number;
  status?: string;
  capabilities?: string[];
  suggestions?: string[];
  info_type?: string;
  user_input_request?: string;
  choices?: string[];
  questions?: string[];
  preferences?: any;
  learning?: any;
  response_type?: string;
  iteration?: number;
  actions?: any[];
  // New agentic fields
  step_number?: number;
  total_steps?: number;
  reasoning?: string;
  decision?: string;
  options?: string[];
  context?: any;
  is_partial?: boolean;
  progress?: number;
}

export interface ToolCall {
  tool: string;
  args: any;
  step: string;
  description: string;
}

export interface ToolResult {
  tool: string;
  step: string;
  result: any;
  success: boolean;
  error?: string;
}

export interface Progress {
  percent: number;
  status: string;
  step: string;
}

export interface ScriptContent {
  id: string;
  content: string;
  timestamp: string;
  tool: string;
}

export interface ProjectFile {
  id: string;
  name: string;
  type: 'video' | 'audio' | 'image' | 'script' | 'voiceover';
  path: string;
  url?: string;  // HTTP URL for displaying images
  size: number;
  timestamp: string;
  thumbnail?: string;
  duration?: number;
  source?: string;
}

export interface VideoPreview {
  id: string;
  path: string;
  timestamp: string;
  status: 'processing' | 'ready' | 'error';
  thumbnail?: string;
}

interface RealtimeStore {
  // Connection state
  connectionStatus: 'connecting' | 'connected' | 'reconnecting' | 'disconnected';
  error: string | null;
  
  // Messages
  messages: Message[];
  toolCalls: ToolCall[];
  toolResults: ToolResult[];
  progress: Progress;
  
  // AI-generated content
  scripts: ScriptContent[];
  projectFiles: ProjectFile[];
  videoPreviews: VideoPreview[];
  
  // File selection
  selectedFile: ProjectFile | null;
  
  // User context
  userContext: {
    style: string;
    tone: string;
    length: string;
    preferences: any;
  };
  
  // Actions
  handleMessage: (msg: Message) => void;
  setConnectionStatus: (status: 'connecting' | 'connected' | 'reconnecting' | 'disconnected') => void;
  setError: (error: string | null) => void;
  clearMessages: () => void;
  addScript: (script: ScriptContent) => void;
  addProjectFile: (file: ProjectFile) => void;
  addVideoPreview: (preview: VideoPreview) => void;
  selectFile: (file: ProjectFile | null) => void;
  updateUserContext: (context: Partial<RealtimeStore['userContext']>) => void;
  clearScripts: () => void;
  clearScriptFiles: () => void;
}

export const useRealtimeStore = create<RealtimeStore>((set, get) => ({
  // Initial state
  connectionStatus: 'disconnected',
  error: null,
  messages: [],
  toolCalls: [],
  toolResults: [],
  progress: { percent: 0, status: '', step: '' },
  scripts: [],
  projectFiles: [],
  videoPreviews: [],
  selectedFile: null,
  userContext: {
    style: 'cinematic',
    tone: 'professional',
    length: 'medium',
    preferences: {}
  },

  // Actions
  handleMessage: (msg) => {
    set((state) => {
      let messages = [...state.messages];
      
      // Check if this is an update to an existing message (same message_id)
      if (msg.message_id && msg.is_partial) {
        const existingIndex = messages.findIndex(m => m.message_id === msg.message_id);
        if (existingIndex !== -1) {
          // Update existing message
          messages[existingIndex] = { ...messages[existingIndex], ...msg };
        } else {
          // Add new message
          messages.push(msg);
        }
      } else {
        // Add new message
        messages.push(msg);
      }
      
      // Handle by type fluidly
      switch (msg.type as MessageType) {
        case "ai_message":
          return { ...state, messages };
          
        case "thinking":
          // Handle thinking messages - these show AI reasoning in real-time
          return { ...state, messages };
          
        case "reasoning":
          // Handle reasoning messages - step-by-step AI thinking process
          return { ...state, messages };
          
        case "tool_execution_start":
        case "tool_execution_complete":
        case "tool_progress":
          // Handle tool execution messages
          return { ...state, messages };
          
        case "decision_context":
        case "decision_option":
        case "decision_made":
          // Handle decision-making messages
          return { ...state, messages };
          
        case "tool_call":
          const toolCall: ToolCall = {
            tool: msg.tool || '',
            args: msg.args || {},
            step: msg.step || '',
            description: msg.description || ''
          };
          return { 
            ...state, 
            toolCalls: [...state.toolCalls, toolCall], 
            messages 
          };
          
        case "tool_result":
          const toolResult: ToolResult = {
            tool: msg.tool || '',
            step: msg.step || '',
            result: msg.result || {},
            success: msg.success || false,
            error: msg.error
          };
          
          // Update project files based on tool results
          let projectFiles = [...state.projectFiles];
          let scripts = [...state.scripts];
          
          if (msg.success && msg.result) {
            if (msg.tool === 'script_writer' && msg.result.script_text) {
              // Add script to scripts array for ScriptTab
              scripts.push({
                id: `script_${Date.now()}`,
                content: msg.result.script_text,
                timestamp: new Date().toISOString(),
                tool: 'script_writer'
              });
              
              // Remove any existing script files from project files
              projectFiles = projectFiles.filter(file => file.type !== 'script');
            }
            if (msg.tool === 'broll_finder' && msg.result) {
              console.log('B-roll finder result:', msg.result);
              
              // Handle downloaded files
              if (msg.result.downloaded_files && msg.result.downloaded_files.length > 0) {
                msg.result.downloaded_files.forEach((file: any) => {
                  projectFiles.push({
                    id: `file_${Date.now()}_${Math.random()}`,
                    name: file.name || 'B-roll Media',
                    type: file.type || 'image',
                    path: file.path,  // Keep original path for reference
                    url: file.url,    // Use URL for display
                    size: file.size || 0,
                    timestamp: new Date().toISOString(),
                    thumbnail: file.url || file.thumbnail,  // Use URL for thumbnail
                    source: file.source || 'unknown'
                  });
                });
                console.log('Added files to project files:', msg.result.downloaded_files.length);
              }
              
              // Handle file paths directly if downloaded_files is empty
              if (msg.result.file_paths && msg.result.file_paths.length > 0 && (!msg.result.downloaded_files || msg.result.downloaded_files.length === 0)) {
                msg.result.file_paths.forEach((filePath: string, index: number) => {
                  const metadata = msg.result.metadata?.[index] || {};
                  
                  // Extract filename and create URL
                  const filename = filePath.split('/').pop() || filePath.split('\\').pop() || '';
                  // Try to extract project ID from the file path or use a default
                  const projectId = filePath.includes('Projects') ? 
                    filePath.split('Projects/')[1]?.split('/')[0] || 'default' : 'default';
                  const imageUrl = `http://127.0.0.1:8001/api/projects/${projectId}/broll/${filename}`;
                  
                  projectFiles.push({
                    id: `file_${Date.now()}_${Math.random()}`,
                    name: metadata.title || `B-roll Media ${index + 1}`,
                    type: metadata.file_type?.toLowerCase() || 'image',
                    path: filePath,
                    url: imageUrl,
                    size: metadata.file_size || 0,
                    timestamp: new Date().toISOString(),
                    thumbnail: imageUrl,
                    source: msg.result.source_types?.[index] || 'unknown'
                  });
                });
                console.log('Added files from file_paths:', msg.result.file_paths.length);
              }
              
              // If there's a helpful message, add it to messages
              if (msg.result.message) {
                messages.push({
                  id: `msg_${Date.now()}`,
                  role: 'assistant',
                  content: msg.result.message,
                  timestamp: new Date().toISOString(),
                  type: 'informational'
                });
              }
              
              // Log the final state
              console.log('Project files after B-roll finder:', projectFiles.length);
            }
            if (msg.tool === 'voiceover_generator' && msg.result.audio_path) {
              projectFiles.push({
                id: `voiceover_${Date.now()}`,
                name: 'Generated Voiceover',
                type: 'voiceover',
                path: msg.result.audio_path,
                size: 0,
                timestamp: new Date().toISOString()
              });
            }
            if (msg.tool === 'video_processor' && msg.result.video_path) {
              projectFiles.push({
                id: `video_${Date.now()}`,
                name: 'Final Video',
                type: 'video',
                path: msg.result.video_path,
                size: 0,
                timestamp: new Date().toISOString(),
                thumbnail: msg.result.thumbnail
              });
              
              // Add to video previews
              const videoPreviews = [...state.videoPreviews, {
                id: `preview_${Date.now()}`,
                path: msg.result.video_path,
                timestamp: new Date().toISOString(),
                status: 'ready',
                thumbnail: msg.result.thumbnail
              }];
              
              return { 
                ...state, 
                toolResults: [...state.toolResults, toolResult], 
                messages,
                projectFiles,
                scripts,
                videoPreviews
              };
            }
          }
          
          return { 
            ...state, 
            toolResults: [...state.toolResults, toolResult], 
            messages,
            projectFiles,
            scripts
          };
          
        case "progress":
          return {
            ...state,
            progress: {
              percent: msg.percent ?? state.progress.percent,
              status: msg.status || '',
              step: msg.step || '',
            },
            messages,
          };
          
        case "error":
          return { ...state, error: msg.detail || msg.message || "Unknown error", messages };
          
        case "connection_established":
          return { ...state, connectionStatus: "connected", messages };
          
        case "approval_received":
          return { ...state, messages };
          
        case "workflow_complete":
          return { ...state, messages };
          
        case "informational":
          return { ...state, messages };
          
        case "interactive":
          return { ...state, messages };
          
        case "adaptive":
          // Update user context from adaptive responses
          const userContext = { ...state.userContext };
          if (msg.preferences) {
            userContext.preferences = { ...userContext.preferences, ...msg.preferences };
          }
          return { ...state, messages, userContext };
          
        case "context_update":
          // Update user context
          const updatedContext = { ...state.userContext };
          if (msg.preferences) {
            updatedContext.preferences = { ...updatedContext.preferences, ...msg.preferences };
          }
          return { ...state, messages, userContext: updatedContext };
          
        case "gui_update":
          // Handle GUI updates from backend
          console.log("🔍 Received GUI update message:", msg);
          let updatedScripts = [...state.scripts];
          let updatedProjectFiles = [...state.projectFiles];
          
          if (msg.update_type === "script_created" && msg.data?.script_content) {
            console.log("🔍 Processing script_created GUI update");
            console.log("🔍 Script content:", msg.data.script_content.substring(0, 100) + "...");
            
            // Add script to scripts array for ScriptTab
            updatedScripts.push({
              id: `script_${Date.now()}`,
              content: msg.data.script_content,
              timestamp: new Date().toISOString(),
              tool: 'script_writer'
            });
            
            // Remove any existing script files from project files
            updatedProjectFiles = updatedProjectFiles.filter(file => file.type !== 'script');
            
            console.log('GUI Update: Script created and added to scripts array');
            console.log('Updated scripts array length:', updatedScripts.length);
          }
          
          if (msg.update_type === "media_downloaded" && msg.data?.downloaded_files) {
            // Handle downloaded media files
            msg.data.downloaded_files.forEach((file: any) => {
              updatedProjectFiles.push({
                id: `file_${Date.now()}_${Math.random()}`,
                name: file.name || 'B-roll Media',
                type: file.type || 'image',
                path: file.path,
                url: file.url,
                size: file.size || 0,
                timestamp: new Date().toISOString(),
                thumbnail: file.url || file.thumbnail,
                source: file.source || 'unknown'
              });
            });
            
            console.log('GUI Update: Media downloaded and added to project files');
          }
          
          if (msg.update_type === "voiceover_created" && msg.data?.voiceover_file) {
            updatedProjectFiles.push({
              id: `voiceover_${Date.now()}`,
              name: 'Generated Voiceover',
              type: 'voiceover',
              path: msg.data.voiceover_file,
              size: 0,
              timestamp: new Date().toISOString()
            });
            
            console.log('GUI Update: Voiceover created and added to project files');
          }
          
          if (msg.update_type === "video_created" && msg.data?.final_video) {
            updatedProjectFiles.push({
              id: `video_${Date.now()}`,
              name: 'Final Video',
              type: 'video',
              path: msg.data.final_video,
              size: 0,
              timestamp: new Date().toISOString()
            });
            
            // Also add to video previews for the video preview panel
            const videoPreviews = [...state.videoPreviews, {
              id: `preview_${Date.now()}`,
              path: msg.data.final_video,
              timestamp: new Date().toISOString(),
              status: 'ready',
              thumbnail: msg.data.thumbnail
            }];
            
            console.log('GUI Update: Video created and added to project files and video previews');
            
            return { 
              ...state, 
              messages,
              scripts: updatedScripts,
              projectFiles: updatedProjectFiles,
              videoPreviews
            };
          }
          
          console.log("🔍 Returning updated state with scripts:", updatedScripts.length);
          return { 
            ...state, 
            messages,
            scripts: updatedScripts,
            projectFiles: updatedProjectFiles
          };
          
        default:
          return { ...state, messages };
      }
    });
  },

  setConnectionStatus: (status) => set({ connectionStatus: status }),
  setError: (error) => set({ error }),
  clearMessages: () => set({ messages: [] }),
  
  addScript: (script) => set((state) => ({
    scripts: [...state.scripts, script]
  })),
  
  addProjectFile: (file) => set((state) => ({
    projectFiles: [...state.projectFiles, file]
  })),
  
  addVideoPreview: (preview) => set((state) => ({
    videoPreviews: [...state.videoPreviews, preview]
  })),

  selectFile: (file) => set({ selectedFile: file }),
  
  updateUserContext: (context) => set((state) => ({
    userContext: { ...state.userContext, ...context }
  })),

  clearScripts: () => set({ scripts: [] }),
  clearScriptFiles: () => set((state) => ({
    projectFiles: state.projectFiles.filter(file => file.type !== 'script')
  }))
})); 