import React from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import { cn } from "./lib/utils";
import './App.css';
import { invoke } from '@tauri-apps/api/core';
import Dashboard from './components/Dashboard';
import { 
  FileVideo, Clapperboard, Text, Wand2, Settings, Play, Pause, SkipBack, SkipForward, 
  Maximize, Download, Send, Sparkles, Layers, Palette, Type, Mic, Upload, 
  Search, Filter, Zap, Plus, Clock, Star, Bookmark, Share, Eye, EyeOff, Lock,
  MoreHorizontal, Grid, List, SortAsc, Folder, Image, Music, Video, FileText,
  Scissors, Copy, Trash2, RotateCcw, RotateCw, ZoomIn, ZoomOut, Maximize2, Minimize2,
  ChevronDown, ChevronRight, Lightbulb, TrendingUp, Award, Target, Settings2, Undo, Redo, 
  RectangleHorizontal, Ratio, Grid3x3, Ruler, PanelRightClose, PanelRightOpen, User, ArrowUp,
  Infinity, AtSign, X, MessageSquare, Sliders, Gauge, Split, Combine, 
  MoveHorizontal, MoveVertical, FlipHorizontal, FlipVertical,
  Menu, Minimize, Square, Minus, Check, Save, RefreshCw, AlertCircle,
  Bot, CornerDownLeft, Paperclip, BrainCircuit, UploadCloud, FilePlus, CheckCircle,
  Film, Sun, Moon, Laptop, ChevronsLeftRight, GripVertical, PanelLeftClose, SlidersHorizontal,
  MousePointer, PlayCircle, PauseCircle, Loader, Volume, ArrowLeft
} from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { useRealtimeStore } from "./hooks/useRealtimeStore";
import { useWebSocket } from "./hooks/useWebSocket";
import { submitPrompt } from "./utils/api";
import StreamingMessage from "./components/StreamingMessage";

// Type definitions
interface AIResponse {
  summary: string;
  details: string[];
}

interface Interaction {
  id: number;
  prompt: string;
  response: AIResponse | null;
}

interface Asset {
  id: string;
  name: string;
  description: string;
  category: string;
}

interface MediaFile {
  id: string;
  name: string;
  type: 'video' | 'audio' | 'image';
  duration?: number;
  thumbnail?: string;
}

interface TimelineClip {
  id: string;
  fileId: string;
  startTime: number;
  duration: number;
  track: number;
}

interface SelectedTag {
  id: string;
  name: string;
  type: 'voice' | 'effect' | 'filter' | 'transition' | 'file';
  displayName: string;
}

// Global state for selected tags
const SelectedTagsContext = React.createContext<{
  selectedTags: SelectedTag[];
  addTag: (tag: SelectedTag) => void;
  removeTag: (tagId: string) => void;
  clearTags: () => void;
}>({
  selectedTags: [],
  addTag: () => {},
  removeTag: () => {},
  clearTags: () => {}
});

const SelectedTagsProvider = ({ children }: { children: React.ReactNode }) => {
  const [selectedTags, setSelectedTags] = useState<SelectedTag[]>([]);

  const addTag = (tag: SelectedTag) => {
    setSelectedTags(prev => {
      // Don't add duplicate tags
      if (prev.some(existingTag => existingTag.id === tag.id)) {
        return prev;
      }
      return [...prev, tag];
    });
  };

  const removeTag = (tagId: string) => {
    setSelectedTags(prev => prev.filter(tag => tag.id !== tagId));
  };

  const clearTags = () => {
    setSelectedTags([]);
  };

  return (
    <SelectedTagsContext.Provider value={{ selectedTags, addTag, removeTag, clearTags }}>
      {children}
    </SelectedTagsContext.Provider>
  );
};

const useSelectedTags = () => {
  const context = React.useContext(SelectedTagsContext);
  if (!context) {
    throw new Error('useSelectedTags must be used within a SelectedTagsProvider');
  }
  return context;
};

const TABS = [
  { key: 'script', label: 'Script', icon: <FileText /> },
  { key: 'effects', label: 'Effects', icon: <Wand2 /> },
  { key: 'filters', label: 'Filters', icon: <Palette /> },
  { key: 'transitions', label: 'Transitions', icon: <Layers /> },
  { key: 'voices', label: 'Voices', icon: <Mic /> },
  { key: 'files', label: 'Project Files', icon: <Folder /> },
];

const mockPromptHistory: string[] = [];

const mockScript = `This is a sample script for your video.\nYou can edit this text to change the narration or on-screen captions.`;

// English Google TTS Voices
const englishVoices = [
  // English (US) - Neural2 voices
  { name: 'en-US-Neural2-A', displayName: 'Neural2 A', accent: 'US', gender: 'Male', technology: 'Neural2' },
  { name: 'en-US-Neural2-C', displayName: 'Neural2 C', accent: 'US', gender: 'Female', technology: 'Neural2' },
  { name: 'en-US-Neural2-D', displayName: 'Neural2 D', accent: 'US', gender: 'Male', technology: 'Neural2' },
  { name: 'en-US-Neural2-E', displayName: 'Neural2 E', accent: 'US', gender: 'Female', technology: 'Neural2' },
  { name: 'en-US-Neural2-F', displayName: 'Neural2 F', accent: 'US', gender: 'Female', technology: 'Neural2' },
  { name: 'en-US-Neural2-G', displayName: 'Neural2 G', accent: 'US', gender: 'Female', technology: 'Neural2' },
  { name: 'en-US-Neural2-H', displayName: 'Neural2 H', accent: 'US', gender: 'Female', technology: 'Neural2' },
  { name: 'en-US-Neural2-I', displayName: 'Neural2 I', accent: 'US', gender: 'Male', technology: 'Neural2' },
  { name: 'en-US-Neural2-J', displayName: 'Neural2 J', accent: 'US', gender: 'Male', technology: 'Neural2' },

  // English (US) - Wavenet voices
  { name: 'en-US-Wavenet-A', displayName: 'Wavenet A', accent: 'US', gender: 'Male', technology: 'Wavenet' },
  { name: 'en-US-Wavenet-B', displayName: 'Wavenet B', accent: 'US', gender: 'Male', technology: 'Wavenet' },
  { name: 'en-US-Wavenet-C', displayName: 'Wavenet C', accent: 'US', gender: 'Female', technology: 'Wavenet' },
  { name: 'en-US-Wavenet-D', displayName: 'Wavenet D', accent: 'US', gender: 'Male', technology: 'Wavenet' },
  { name: 'en-US-Wavenet-E', displayName: 'Wavenet E', accent: 'US', gender: 'Female', technology: 'Wavenet' },
  { name: 'en-US-Wavenet-F', displayName: 'Wavenet F', accent: 'US', gender: 'Female', technology: 'Wavenet' },
  { name: 'en-US-Wavenet-G', displayName: 'Wavenet G', accent: 'US', gender: 'Female', technology: 'Wavenet' },
  { name: 'en-US-Wavenet-H', displayName: 'Wavenet H', accent: 'US', gender: 'Female', technology: 'Wavenet' },
  { name: 'en-US-Wavenet-I', displayName: 'Wavenet I', accent: 'US', gender: 'Male', technology: 'Wavenet' },
  { name: 'en-US-Wavenet-J', displayName: 'Wavenet J', accent: 'US', gender: 'Male', technology: 'Wavenet' },

  // English (US) - Standard voices
  { name: 'en-US-Standard-A', displayName: 'Standard A', accent: 'US', gender: 'Male', technology: 'Standard' },
  { name: 'en-US-Standard-B', displayName: 'Standard B', accent: 'US', gender: 'Male', technology: 'Standard' },
  { name: 'en-US-Standard-C', displayName: 'Standard C', accent: 'US', gender: 'Female', technology: 'Standard' },
  { name: 'en-US-Standard-D', displayName: 'Standard D', accent: 'US', gender: 'Male', technology: 'Standard' },
  { name: 'en-US-Standard-E', displayName: 'Standard E', accent: 'US', gender: 'Female', technology: 'Standard' },
  { name: 'en-US-Standard-F', displayName: 'Standard F', accent: 'US', gender: 'Female', technology: 'Standard' },
  { name: 'en-US-Standard-G', displayName: 'Standard G', accent: 'US', gender: 'Female', technology: 'Standard' },
  { name: 'en-US-Standard-H', displayName: 'Standard H', accent: 'US', gender: 'Female', technology: 'Standard' },
  { name: 'en-US-Standard-I', displayName: 'Standard I', accent: 'US', gender: 'Male', technology: 'Standard' },
  { name: 'en-US-Standard-J', displayName: 'Standard J', accent: 'US', gender: 'Male', technology: 'Standard' },

  // English (UK) - Neural2 voices
  { name: 'en-GB-Neural2-A', displayName: 'Neural2 A', accent: 'UK', gender: 'Female', technology: 'Neural2' },
  { name: 'en-GB-Neural2-B', displayName: 'Neural2 B', accent: 'UK', gender: 'Male', technology: 'Neural2' },
  { name: 'en-GB-Neural2-C', displayName: 'Neural2 C', accent: 'UK', gender: 'Female', technology: 'Neural2' },
  { name: 'en-GB-Neural2-D', displayName: 'Neural2 D', accent: 'UK', gender: 'Male', technology: 'Neural2' },
  { name: 'en-GB-Neural2-F', displayName: 'Neural2 F', accent: 'UK', gender: 'Female', technology: 'Neural2' },

  // English (UK) - Wavenet voices
  { name: 'en-GB-Wavenet-A', displayName: 'Wavenet A', accent: 'UK', gender: 'Female', technology: 'Wavenet' },
  { name: 'en-GB-Wavenet-B', displayName: 'Wavenet B', accent: 'UK', gender: 'Male', technology: 'Wavenet' },
  { name: 'en-GB-Wavenet-C', displayName: 'Wavenet C', accent: 'UK', gender: 'Female', technology: 'Wavenet' },
  { name: 'en-GB-Wavenet-D', displayName: 'Wavenet D', accent: 'UK', gender: 'Male', technology: 'Wavenet' },
  { name: 'en-GB-Wavenet-F', displayName: 'Wavenet F', accent: 'UK', gender: 'Female', technology: 'Wavenet' },

  // English (UK) - Standard voices
  { name: 'en-GB-Standard-A', displayName: 'Standard A', accent: 'UK', gender: 'Female', technology: 'Standard' },
  { name: 'en-GB-Standard-B', displayName: 'Standard B', accent: 'UK', gender: 'Male', technology: 'Standard' },
  { name: 'en-GB-Standard-C', displayName: 'Standard C', accent: 'UK', gender: 'Female', technology: 'Standard' },
  { name: 'en-GB-Standard-D', displayName: 'Standard D', accent: 'UK', gender: 'Male', technology: 'Standard' },
  { name: 'en-GB-Standard-F', displayName: 'Standard F', accent: 'UK', gender: 'Female', technology: 'Standard' },

  // English (Australia) - Neural2 voices
  { name: 'en-AU-Neural2-A', displayName: 'Neural2 A', accent: 'AU', gender: 'Female', technology: 'Neural2' },
  { name: 'en-AU-Neural2-B', displayName: 'Neural2 B', accent: 'AU', gender: 'Male', technology: 'Neural2' },
  { name: 'en-AU-Neural2-C', displayName: 'Neural2 C', accent: 'AU', gender: 'Female', technology: 'Neural2' },
  { name: 'en-AU-Neural2-D', displayName: 'Neural2 D', accent: 'AU', gender: 'Male', technology: 'Neural2' },

  // English (Australia) - Wavenet voices
  { name: 'en-AU-Wavenet-A', displayName: 'Wavenet A', accent: 'AU', gender: 'Female', technology: 'Wavenet' },
  { name: 'en-AU-Wavenet-B', displayName: 'Wavenet B', accent: 'AU', gender: 'Male', technology: 'Wavenet' },
  { name: 'en-AU-Wavenet-C', displayName: 'Wavenet C', accent: 'AU', gender: 'Female', technology: 'Wavenet' },
  { name: 'en-AU-Wavenet-D', displayName: 'Wavenet D', accent: 'AU', gender: 'Male', technology: 'Wavenet' },

  // English (Australia) - Standard voices
  { name: 'en-AU-Standard-A', displayName: 'Standard A', accent: 'AU', gender: 'Female', technology: 'Standard' },
  { name: 'en-AU-Standard-B', displayName: 'Standard B', accent: 'AU', gender: 'Male', technology: 'Standard' },
  { name: 'en-AU-Standard-C', displayName: 'Standard C', accent: 'AU', gender: 'Female', technology: 'Standard' },
  { name: 'en-AU-Standard-D', displayName: 'Standard D', accent: 'AU', gender: 'Male', technology: 'Standard' },

  // English (India) - Neural2 voices
  { name: 'en-IN-Neural2-A', displayName: 'Neural2 A', accent: 'IN', gender: 'Female', technology: 'Neural2' },
  { name: 'en-IN-Neural2-B', displayName: 'Neural2 B', accent: 'IN', gender: 'Male', technology: 'Neural2' },
  { name: 'en-IN-Neural2-C', displayName: 'Neural2 C', accent: 'IN', gender: 'Male', technology: 'Neural2' },
  { name: 'en-IN-Neural2-D', displayName: 'Neural2 D', accent: 'IN', gender: 'Female', technology: 'Neural2' },

  // English (India) - Wavenet voices
  { name: 'en-IN-Wavenet-A', displayName: 'Wavenet A', accent: 'IN', gender: 'Female', technology: 'Wavenet' },
  { name: 'en-IN-Wavenet-B', displayName: 'Wavenet B', accent: 'IN', gender: 'Male', technology: 'Wavenet' },
  { name: 'en-IN-Wavenet-C', displayName: 'Wavenet C', accent: 'IN', gender: 'Male', technology: 'Wavenet' },
  { name: 'en-IN-Wavenet-D', displayName: 'Wavenet D', accent: 'IN', gender: 'Female', technology: 'Wavenet' },

  // English (India) - Standard voices
  { name: 'en-IN-Standard-A', displayName: 'Standard A', accent: 'IN', gender: 'Female', technology: 'Standard' },
  { name: 'en-IN-Standard-B', displayName: 'Standard B', accent: 'IN', gender: 'Male', technology: 'Standard' },
  { name: 'en-IN-Standard-C', displayName: 'Standard C', accent: 'IN', gender: 'Male', technology: 'Standard' },
  { name: 'en-IN-Standard-D', displayName: 'Standard D', accent: 'IN', gender: 'Female', technology: 'Standard' },
];

// Custom Title Bar Component
const CustomTitleBar = () => {
  const [projectName, setProjectName] = useState('Untitled Project');
  const [isEditing, setIsEditing] = useState(false);

  const handleProjectNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setProjectName(e.target.value);
  };

  const handleProjectNameSubmit = () => {
    setIsEditing(false);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleProjectNameSubmit();
    }
    if (e.key === 'Escape') {
      setIsEditing(false);
    }
  };

  return (
  <div className="custom-title-bar">
    <div className="title-bar-left">
      <button className="title-bar-menu">
        <Menu size={14} />
      </button>
    </div>
    <div className="title-bar-center">
        <span style={{marginRight: '8px', color: 'var(--accent-blue)', fontWeight: 600}}>Sclips</span>
        <span style={{marginRight: '8px'}}>•</span>
        {isEditing ? (
          <input
            type="text"
            value={projectName}
            onChange={handleProjectNameChange}
            onBlur={handleProjectNameSubmit}
            onKeyPress={handleKeyPress}
            autoFocus
            style={{
              background: 'transparent',
              border: '1px solid var(--accent-blue)',
              borderRadius: '4px',
              padding: '2px 6px',
              color: 'var(--text-primary)',
              fontSize: '13px',
              outline: 'none',
              minWidth: '120px'
            }}
          />
        ) : (
          <span 
            onClick={() => setIsEditing(true)}
            style={{
              cursor: 'pointer',
              padding: '2px 6px',
              borderRadius: '4px',
              transition: 'background var(--transition-fast)'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(59, 130, 246, 0.1)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
            }}
          >
            {projectName}
          </span>
        )}
    </div>
    <div className="title-bar-right">
      <button className="window-control">
        <Minus size={16} />
      </button>
      <button className="window-control">
        <Square size={14} />
      </button>
      <button className="window-control close">
        <X size={16} />
      </button>
    </div>
  </div>
);
};

// Re-add the TagMenu component definition above AIChatPanel
const TagMenu = ({ onSelect, onClose }: { onSelect: (tag: string) => void, onClose: () => void }) => {
  const menuRef = useRef<HTMLDivElement>(null);
  const [searchTerm, setSearchTerm] = useState('');

  const tagCategories = [
    {
      category: "Transitions",
      icon: <Layers className="w-4 h-4" />,
      tags: ["@crossfade", "@wipe-left", "@slide-down", "@iris-in", "@push-left", "@circle-wipe"]
    },
    {
      category: "Effects",
      icon: <Wand2 className="w-4 h-4" />,
      tags: ["@zoom-in", "@shake", "@glitch", "@focus-pull", "@lens-flare", "@particle-burst"]
    },
    {
      category: "Filters",
      icon: <Palette className="w-4 h-4" />,
      tags: ["@vintage", "@b&w", "@sepia", "@technicolor", "@cyberpunk", "@film-grain"]
    },
    {
      category: "Audio",
      icon: <Music className="w-4 h-4" />,
      tags: ["@fade-in", "@echo", "@reverb", "@auto-duck", "@beat-sync", "@voice-enhance"]
    }
  ];

  const filteredCategories = tagCategories.map(category => ({
    ...category,
    tags: category.tags.filter(tag =>
      tag.toLowerCase().includes(searchTerm.toLowerCase())
    )
  })).filter(category => category.tags.length > 0);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onClose();
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [onClose]);

  return (
    <div ref={menuRef} className="tag-menu">
      <div className="tag-menu-search">
        <Search className="w-4 h-4 text-gray-400" />
        <input
          type="text"
          placeholder="Search effects, transitions..."
          className="tag-menu-input"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          autoFocus
        />
      </div>
      <div className="tag-menu-content">
        {filteredCategories.map(({ category, icon, tags }) => (
          <div key={category} className="tag-category">
            <div className="tag-category-header">
              <span className="category-icon">{icon}</span>
              <span className="category-name">{category}</span>
            </div>
            <div className="tag-grid">
              {tags.map(tag => (
                <button key={tag} className="tag-item" onClick={() => onSelect(tag)}>
                  <span>{tag}</span>
                  <div className="tag-preview">
                    <Sparkles className="w-3 h-3" />
                  </div>
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Enhanced AI Panel with Advanced Features
const AIChatPanel = ({ currentProject }: { currentProject?: any }) => {
  const { selectedTags, clearTags } = useSelectedTags();
  const [inputValue, setInputValue] = useState('');
  const messages = useRealtimeStore((s) => s.messages);
  const connectionStatus = useRealtimeStore((s) => s.connectionStatus);
  const [sessionId, setSessionId] = useState<string>("");
  const [isProcessing, setIsProcessing] = useState(false);
  
  // Initialize sessionId once when component mounts
  useEffect(() => {
    if (!sessionId) {
      const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      setSessionId(newSessionId);
    }
  }, [sessionId]);
  
  const { sendMessage } = useWebSocket({ sessionId });

  const handleSend = async () => {
    if (!inputValue.trim() || isProcessing) return;
    
    setIsProcessing(true);
    
    // Get current frontend state from Zustand store
    const currentState = useRealtimeStore.getState();
    const frontendState = {
      scripts: currentState.scripts,
      projectFiles: currentState.projectFiles,
      videoPreviews: currentState.videoPreviews,
      userContext: currentState.userContext,
      messages: currentState.messages
    };
    
    // Add user message to Zustand store immediately
    useRealtimeStore.getState().handleMessage({
      type: 'user_message',
      content: inputValue,
      timestamp: new Date().toISOString(),
      session_id: sessionId,
    });
    
    // Send message via WebSocket with frontend state
    sendMessage({ 
      type: 'user_message', 
      content: inputValue,
      project_id: currentProject?.id,
      frontend_state: frontendState
    });
    
    setInputValue('');
    
    // Reset processing state after a delay to allow for streaming
    setTimeout(() => {
      setIsProcessing(false);
    }, 1000);
  };

  // Auto-scroll to bottom when new messages arrive
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  return (
    <div className="floating-panel">
      <div className="floating-panel-header ai-panel-header-compact">
        <div className="ai-panel-title">
          <Bot size={18} />
          <span>AI Assistant</span>
        </div>
        <div className={`ai-conn-indicator status-${connectionStatus}`} title={`Session: ${sessionId}`}>
          <span className="dot" />
          <span className="label">{connectionStatus}</span>
        </div>
        {isProcessing && (
          <div className="processing-indicator">
            <div className="processing-dots">
              <span className="dot"></span>
              <span className="dot"></span>
              <span className="dot"></span>
            </div>
          </div>
        )}
      </div>
      <div className="floating-panel-body ai-chat-body">
        {messages
          .filter(message => message.type !== "connection_established") // Filter out connection messages
          .map((message, idx) => (
            <StreamingMessage
              key={message.message_id || message.timestamp || idx}
              message={message}
              streamingSpeed={15} // Faster streaming
              onComplete={() => {
                // Optional: Add any completion logic here
              }}
            />
          ))}
        <div ref={messagesEndRef} />
      </div>
      <div className="ai-chat-input-container">
        <div className="ai-chat-input-wrapper">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder={selectedTags.length > 0 ? "Describe what you want to do with the selected items..." : "Ask AI to create a video, write a script, or help with editing (Press Enter)…"}
            className="ai-chat-input"
            disabled={isProcessing}
          />
          <div className="ai-input-hint">⌘K for commands</div>
          <button 
            className={`ai-chat-send-btn ${isProcessing ? 'processing' : ''}`} 
            onClick={handleSend}
            disabled={isProcessing}
          >
            {isProcessing ? (
              <div className="loading-spinner"></div>
            ) : (
              <CornerDownLeft size={18} />
            )}
          </button>
        </div>
        <div className="ai-chat-actions">
          <button className="ai-action-btn" title="Video Templates">
            <BrainCircuit size={16} />
            <span>Video Templates</span>
          </button>
        </div>
      </div>
    </div>
  );
};

// Enhanced Timeline Component with Visual Representation
const EnhancedTimeline = () => {
  const [clips] = useState<TimelineClip[]>([
    { id: '1', fileId: 'clip1', startTime: 0, duration: 147, track: 0 },
    { id: '2', fileId: 'clip2', startTime: 147, duration: 70, track: 0 },
    { id: '3', fileId: 'audio1', startTime: 0, duration: 217, track: 1 },
  ]);
  const [currentTime, setCurrentTime] = useState(45);
  const [zoom, setZoom] = useState(50);
  const [isPlaying, setIsPlaying] = useState(false);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const timelineWidth = 800;
  const maxDuration = Math.max(...clips.map(clip => clip.startTime + clip.duration));
  const pixelsPerSecond = (timelineWidth * zoom / 100) / maxDuration;

  return (
    <div className="enhanced-timeline">
      {/* Timeline Header */}
      <div className="timeline-header">
        <div className="timeline-tools">
          <button className="timeline-tool-btn active">
            <MousePointer className="w-4 h-4" />
          </button>
          <button className="timeline-tool-btn">
            <Scissors className="w-4 h-4" />
          </button>
          <button className="timeline-tool-btn">
            <Split className="w-4 h-4" />
          </button>
          <div className="tool-divider" />
          <button className="timeline-tool-btn">
            <ZoomOut className="w-4 h-4" />
          </button>
          <div className="zoom-control">
            <input 
              type="range" 
              min="10" 
              max="200" 
              value={zoom}
              onChange={(e) => setZoom(Number(e.target.value))}
              className="zoom-slider"
            />
            <span className="zoom-label">{zoom}%</span>
          </div>
          <button className="timeline-tool-btn">
            <ZoomIn className="w-4 h-4" />
          </button>
        </div>
        
        <div className="timeline-playback">
          <button 
            className="playback-btn"
            onClick={() => setIsPlaying(!isPlaying)}
          >
            {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          </button>
          <div className="time-display">
            <span className="current-time">{formatTime(currentTime)}</span>
            <span className="separator">/</span>
            <span className="total-time">{formatTime(maxDuration)}</span>
          </div>
        </div>
      </div>

      {/* Timeline Content */}
      <div className="timeline-content">
        {/* Track Headers */}
        <div className="track-headers">
          <div className="track-header video-track">
            <Video className="w-4 h-4" />
            <span>Video</span>
            <button className="track-mute-btn">
              <Volume className="w-3 h-3" />
            </button>
          </div>
          <div className="track-header audio-track">
            <Music className="w-4 h-4" />
            <span>Audio</span>
            <button className="track-mute-btn">
              <Volume className="w-3 h-3" />
            </button>
          </div>
        </div>
        
        {/* Timeline Area */}
        <div className="timeline-area" style={{ width: timelineWidth }}>
          {/* Time Ruler */}
          <div className="time-ruler">
            {Array.from({ length: Math.ceil(maxDuration / 10) + 1 }, (_, i) => (
              <div 
                key={i} 
                className="time-marker"
                style={{ left: `${(i * 10) * pixelsPerSecond}px` }}
              >
                <span>{formatTime(i * 10)}</span>
              </div>
            ))}
          </div>

          {/* Tracks */}
          <div className="timeline-tracks">
            {/* Video Track */}
            <div className="timeline-track video-track">
              {clips
                .filter(clip => clip.track === 0)
                .map(clip => (
                  <div
                    key={clip.id}
                    className="timeline-clip video-clip"
                    style={{
                      left: `${clip.startTime * pixelsPerSecond}px`,
                      width: `${clip.duration * pixelsPerSecond}px`
                    }}
                  >
                    <div className="clip-content">
                      <span className="clip-name">{clip.fileId}.mp4</span>
                      <div className="clip-waveform">
                        {Array.from({ length: 20 }, (_, i) => (
                          <div 
                            key={i} 
                            className="waveform-bar"
                            style={{ height: `${Math.random() * 60 + 20}%` }}
                          />
                        ))}
          </div>
        </div>
                    <div className="clip-resize-handle left" />
                    <div className="clip-resize-handle right" />
                  </div>
                ))}
      </div>

            {/* Audio Track */}
            <div className="timeline-track audio-track">
              {clips
                .filter(clip => clip.track === 1)
                .map(clip => (
                  <div
                    key={clip.id}
                    className="timeline-clip audio-clip"
                    style={{
                      left: `${clip.startTime * pixelsPerSecond}px`,
                      width: `${clip.duration * pixelsPerSecond}px`
                    }}
                  >
                    <div className="clip-content">
                      <span className="clip-name">{clip.fileId}.mp3</span>
                      <div className="audio-waveform">
                        {Array.from({ length: 40 }, (_, i) => (
                          <div 
                            key={i} 
                            className="waveform-bar"
                            style={{ height: `${Math.random() * 80 + 10}%` }}
                          />
                        ))}
                      </div>
                    </div>
                    <div className="clip-resize-handle left" />
                    <div className="clip-resize-handle right" />
            </div>
          ))}
            </div>
          </div>

          {/* Playhead */}
          <div 
            className="timeline-playhead"
            style={{ left: `${currentTime * pixelsPerSecond}px` }}
          >
            <div className="playhead-line" />
            <div className="playhead-handle" />
          </div>
        </div>
      </div>
    </div>
  );
};

// Completely Enhanced Video Editor
const ProfessionalVideoEditor = () => {
  const [selectedTool, setSelectedTool] = useState('select');
  const [selectedClip, setSelectedClip] = useState<string | null>(null);
  const [previewFile, setPreviewFile] = useState<any>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(80);

  const tools = [
    { id: 'select', icon: MousePointer, label: 'Select Tool' },
    { id: 'cut', icon: Scissors, label: 'Cut Tool' },
    { id: 'text', icon: Type, label: 'Text Tool' },
    { id: 'transition', icon: Zap, label: 'Transition Tool' },
  ];

  const effects = [
    { id: 'blur', name: 'Blur', icon: '🌫️' },
    { id: 'sharpen', name: 'Sharpen', icon: '🔍' },
    { id: 'vintage', name: 'Vintage', icon: '📸' },
    { id: 'neon', name: 'Neon', icon: '💫' },
  ];

  return (
    <div className="professional-video-editor">
      {/* Main Editor Area */}
      <div className="editor-workspace">
        {/* Left Sidebar - Tools & Effects */}
        <div className="editor-sidebar left">
          <div className="tool-panel">
            <h3 className="panel-title">Tools</h3>
            <div className="tool-grid">
              {tools.map(tool => (
                <button
                  key={tool.id}
                  className={`tool-btn ${selectedTool === tool.id ? 'active' : ''}`}
                  onClick={() => setSelectedTool(tool.id)}
                  title={tool.label}
                >
                  <tool.icon className="w-5 h-5" />
                  <span>{tool.label}</span>
                </button>
              ))}
          </div>
        </div>
        
          <div className="effects-panel">
            <h3 className="panel-title">Effects</h3>
            <div className="effects-grid">
              {effects.map(effect => (
                <div key={effect.id} className="effect-item">
                  <div className="effect-preview">
                    <span className="effect-icon">{effect.icon}</span>
          </div>
                  <span className="effect-name">{effect.name}</span>
        </div>
              ))}
        </div>
      </div>
        </div>

        {/* Center - Video Preview */}
        <div className="editor-center">
          <div className="video-preview-area">
          <div className="preview-container">
              {previewFile ? (
                <div className="video-preview-active">
                  <div className="video-frame">
                    <div className="video-content">
                      <FileVideo className="w-16 h-16 text-gray-400" />
                      <p className="preview-text">Playing: {previewFile.name}</p>
              </div>
              
                    {/* Preview Overlay Controls */}
                    <div className="preview-overlay">
                      <button 
                        className="play-overlay-btn"
                        onClick={() => setIsPlaying(!isPlaying)}
                      >
                        {isPlaying ? <Pause className="w-8 h-8" /> : <Play className="w-8 h-8" />}
                      </button>
                    </div>
                  </div>
                  
                  {/* Preview Controls */}
              <div className="preview-controls">
                    <div className="control-row">
                      <button 
                        className="control-btn"
                        onClick={() => setIsPlaying(!isPlaying)}
                      >
                        {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                      </button>
                      
                      <div className="timeline-scrubber">
                        <input
                          type="range"
                          min="0"
                          max="100"
                          value={currentTime}
                          onChange={(e) => setCurrentTime(Number(e.target.value))}
                          className="scrubber-slider"
                        />
                      </div>
                      
                <div className="volume-control">
                  <Volume className="w-4 h-4" />
        <input
                    type="range" 
                    min="0" 
                    max="100" 
                    value={volume} 
                    onChange={(e) => setVolume(Number(e.target.value))}
                    className="volume-slider"
                  />
                </div>
                      
                      <button className="control-btn">
                  <Maximize className="w-4 h-4" />
                </button>
              </div>
                  </div>
                </div>
              ) : (
                <div className="preview-placeholder">
                  <FileVideo className="w-20 h-20 text-gray-500" />
                  <h3>Select a video to preview</h3>
                  <p>Choose a file from the project panel to start editing</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Sidebar - Properties */}
        <div className="editor-sidebar right">
          <div className="properties-panel">
            <div className="property-tabs">
              <button className="property-tab active">Transform</button>
              <button className="property-tab">Color</button>
              <button className="property-tab">Audio</button>
          </div>
          
            <div className="property-content">
            <div className="property-section">
                <h4 className="property-title">Position & Scale</h4>
                <div className="property-controls">
                  <div className="control-group">
                  <label>X Position</label>
                    <input type="number" defaultValue="0" className="control-input" />
                </div>
                  <div className="control-group">
                  <label>Y Position</label>
                    <input type="number" defaultValue="0" className="control-input" />
                </div>
                  <div className="control-group">
                    <label>Scale</label>
                    <input type="range" min="0" max="200" defaultValue="100" className="control-slider" />
                  </div>
                  <div className="control-group">
                    <label>Rotation</label>
                    <input type="range" min="-180" max="180" defaultValue="0" className="control-slider" />
                  </div>
              </div>
            </div>

            <div className="property-section">
                <h4 className="property-title">Color Grading</h4>
                <div className="property-controls">
                  <div className="control-group">
                  <label>Brightness</label>
                    <input type="range" min="-100" max="100" defaultValue="0" className="control-slider" />
                </div>
                  <div className="control-group">
                  <label>Contrast</label>
                    <input type="range" min="-100" max="100" defaultValue="0" className="control-slider" />
                </div>
                  <div className="control-group">
                  <label>Saturation</label>
                    <input type="range" min="-100" max="100" defaultValue="0" className="control-slider" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Timeline Area */}
      <div className="editor-timeline">
        <EnhancedTimeline />
      </div>
    </div>
  );
};

// Main Video Editor Layout
const VideoEditor = () => <ProfessionalVideoEditor />;

// Enhanced File Management Component
const FilesPanel = ({ onFileSelect, selectedFile, onFileRemoved, currentProject }: { 
  onFileSelect?: (file: any) => void,
  selectedFile?: any,
  onFileRemoved?: () => void,
  currentProject?: any
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [fileFilter, setFileFilter] = useState('all');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('list');
  const [dragOver, setDragOver] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<any[]>([]);
  const [projectFiles, setProjectFiles] = useState<any[]>([]);
  const [isLoadingProjectFiles, setIsLoadingProjectFiles] = useState(false);
  const { addTag } = useSelectedTags();
  
  // Get AI-generated files from realtime store (for backward compatibility)
  const globalProjectFiles = useRealtimeStore((s) => s.projectFiles);
  const isDownloading = useRealtimeStore((s) => 
    s.toolCalls.some(call => call.tool === "broll_finder")
  );
  
  // Load project files when currentProject changes
  useEffect(() => {
    const loadProjectFiles = async () => {
      if (!currentProject?.id) {
        setProjectFiles([]);
        return;
      }
      
      try {
        setIsLoadingProjectFiles(true);
        const response = await fetch(`http://127.0.0.1:8001/api/projects/${currentProject.id}/files`);
        if (response.ok) {
          const files = await response.json();
          setProjectFiles(files);
        } else {
          console.error('Failed to load project files');
          setProjectFiles([]);
        }
      } catch (error) {
        console.error('Error loading project files:', error);
        setProjectFiles([]);
      } finally {
        setIsLoadingProjectFiles(false);
      }
    };
    
    loadProjectFiles();
  }, [currentProject?.id]);

  // Refresh project files when B-roll finder completes
  useEffect(() => {
    const refreshProjectFiles = async () => {
      if (!currentProject?.id || !isDownloading) return;
      
      // Wait a bit for files to be downloaded, then refresh
      setTimeout(async () => {
        try {
          const response = await fetch(`http://127.0.0.1:8001/api/projects/${currentProject.id}/files`);
          if (response.ok) {
            const files = await response.json();
            setProjectFiles(files);
            console.log('Refreshed project files after B-roll download:', files.length);
          }
        } catch (error) {
          console.error('Error refreshing project files:', error);
        }
      }, 2000); // Wait 2 seconds for download to complete
    };
    
    refreshProjectFiles();
  }, [isDownloading, currentProject?.id]);
  
  // Combine uploaded files with project files and global project files
  // Prioritize project files from API over global project files to avoid placeholders
  const allFiles = [...uploadedFiles, ...projectFiles, ...globalProjectFiles.filter(file => 
    // Only include global project files that are not placeholders and not already in projectFiles
    !file.name.toLowerCase().includes('placeholder') && 
    !projectFiles.some(pf => pf.name === file.name)
  )];

  // Remove file handler
  const handleRemoveFile = (fileName: string) => {
    setUploadedFiles(prev => prev.filter(f => f.name !== fileName));
    // If the removed file was currently selected, clear the preview
    if (selectedFile && selectedFile.name === fileName && onFileRemoved) {
      onFileRemoved();
    }
  };

  // Filter files based on search and filter
  const filteredFiles = allFiles.filter(file => {
    const matchesSearch = file.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = fileFilter === 'all' || file.type === fileFilter;
    return matchesSearch && matchesFilter;
  });

  const handleFileClick = (file: any) => {
    // Construct the proper file object for preview
    let previewFile = { ...file };
    
    // If this is a project file (from API), construct the proper URL
    if (file.path && currentProject?.id) {
      // Check if it's a B-roll file (in broll folder)
      if (file.folder === 'broll') {
        previewFile.url = `http://127.0.0.1:8001/api/projects/${currentProject.id}/broll/${file.name}`;
      } else {
        // For other project files, use the general file serving endpoint
        previewFile.url = `http://127.0.0.1:8001/api/projects/${currentProject.id}/files/${file.name}`;
      }
    }
    
    if (onFileSelect) {
      onFileSelect(previewFile);
    }
    // Add file as a tag
    addTag({
      id: file.name,
      name: file.name,
      type: 'file',
      displayName: file.name,
    });
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleFileUpload(files);
    }
  };

  // Add uploaded files to state
  const handleFileUpload = (fileList: FileList) => {
    const newFiles = Array.from(fileList).map(file => {
      const fileType = file.type.startsWith('video/') ? 'video' : 
                      file.type.startsWith('audio/') ? 'audio' : 'image';
      return {
        name: file.name,
        type: fileType,
        size: file.size,
        duration: undefined, // Could be set with extra logic for video/audio
        file: file,
      };
    });
    setUploadedFiles(prev => [...prev, ...newFiles]);
  };

  const handleBrowseFiles = () => {
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = 'video/*,audio/*,image/*';
    fileInput.multiple = true;
    fileInput.onchange = (e) => {
      const target = e.target as HTMLInputElement;
      const files = target.files;
      if (files && files.length > 0) {
        handleFileUpload(files);
      }
    };
    fileInput.click();
  };

  return (
    <div className="panel-content-wrapper">
      <div className="panel-header">
        📁 Project Files
        </div>
      
      <div className="tab-content-area">
        {/* Search and Filter Bar */}
        <div style={{
          display: 'flex',
          gap: '8px',
          marginBottom: '16px',
          alignItems: 'center'
        }}>
          <div style={{
            flex: 1,
            position: 'relative'
          }}>
            <Search style={{
              position: 'absolute',
              left: '8px',
              top: '50%',
              transform: 'translateY(-50%)',
              width: '14px',
              height: '14px',
              color: 'var(--text-muted)'
            }} />
            <input
              type="text"
              placeholder="Search files..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                width: '100%',
                background: 'var(--gradient-surface)',
                border: '1px solid var(--border-primary)',
                borderRadius: 'var(--radius-md)',
                padding: '6px 8px 6px 28px',
                color: 'var(--text-primary)',
                fontSize: '13px',
                outline: 'none'
              }}
            />
          </div>
          {/* Mini Add File Button */}
          <button
            onClick={handleBrowseFiles}
            style={{
              background: 'var(--gradient-accent)',
              border: 'none',
              borderRadius: 'var(--radius-md)',
              padding: '6px 10px',
              color: 'white',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: 'var(--shadow-moderate)'
            }}
            title="Add File"
          >
            <Upload style={{width: '16px', height: '16px'}} />
          </button>
          
          <select
            value={fileFilter}
            onChange={(e) => setFileFilter(e.target.value)}
            style={{
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-primary)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-primary)',
              padding: '6px 8px',
              fontSize: '13px'
            }}
          >
            <option value="all">All Files</option>
            <option value="video">Videos</option>
            <option value="audio">Audio</option>
            <option value="image">Images</option>
          </select>

          <div style={{display: 'flex', gap: '4px'}}>
            <button
              onClick={() => setViewMode('list')}
              style={{
                background: viewMode === 'list' ? 'var(--gradient-accent)' : 'var(--bg-tertiary)',
                border: '1px solid var(--border-primary)',
                borderRadius: 'var(--radius-sm)',
                padding: '6px',
                color: viewMode === 'list' ? 'white' : 'var(--text-secondary)',
                cursor: 'pointer'
              }}
            >
              <List style={{width: '14px', height: '14px'}} />
          </button>
            <button
              onClick={() => setViewMode('grid')}
              style={{
                background: viewMode === 'grid' ? 'var(--gradient-accent)' : 'var(--bg-tertiary)',
                border: '1px solid var(--border-primary)',
                borderRadius: 'var(--radius-sm)',
                padding: '6px',
                color: viewMode === 'grid' ? 'white' : 'var(--text-secondary)',
                cursor: 'pointer'
              }}
            >
              <Grid3x3 style={{width: '14px', height: '14px'}} />
          </button>
        </div>
      </div>
      


        {/* All Files Section */}
        <div>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '8px'
          }}>
          <h4 style={{
            fontSize: '12px',
            fontWeight: 600,
            color: 'var(--text-muted)',
            textTransform: 'uppercase',
              letterSpacing: '0.5px',
              margin: 0
          }}>
            Project Files ({filteredFiles.length})
          </h4>
            {isDownloading && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                color: '#4facfe',
                fontSize: '11px'
              }}>
                <div style={{ 
                  width: 12, 
                  height: 12, 
                  border: "2px solid #4facfe", 
                  borderTop: "2px solid transparent", 
                  borderRadius: "50%", 
                  animation: "spin 1s linear infinite",
                  marginRight: 6 
                }}></div>
                AI downloading media...
              </div>
            )}
          </div>
          
          {viewMode === 'list' ? (
            <div className="files-list">
              {filteredFiles.map(file => (
                <div 
                  className="file-row"
                  key={file.name}
                  onClick={() => handleFileClick(file)}
                  style={{
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    padding: '10px 14px',
                    borderRadius: '8px',
                    marginBottom: '8px',
                    background: selectedFile && selectedFile.name === file.name ? 'var(--gradient-accent)' : 'var(--bg-tertiary)',
                    transition: 'background 0.15s',
                    boxShadow: selectedFile && selectedFile.name === file.name ? 'var(--shadow-moderate)' : '0 1px 4px rgba(0,0,0,0.03)',
                    position: 'relative',
                    gap: '12px',
                    border: selectedFile && selectedFile.name === file.name ? '1px solid var(--accent-primary)' : 'none',
                  }}
                  onMouseEnter={e => {
                    if (!selectedFile || selectedFile.name !== file.name) {
                      e.currentTarget.style.background = 'var(--gradient-surface)';
                    }
                  }}
                  onMouseLeave={e => {
                    if (!selectedFile || selectedFile.name !== file.name) {
                      e.currentTarget.style.background = 'var(--bg-tertiary)';
                    }
                  }}
                >
                  <div className="file-icon" style={{marginRight: '10px', fontSize: '20px', position: 'relative'}}>
                    {file.type === 'video' ? '🎬' : file.type === 'audio' ? '🎵' : '🖼️'}
                    {selectedFile && selectedFile.name === file.name && (
                      <div style={{
                        position: 'absolute',
                        top: '-2px',
                        right: '-2px',
                        width: '8px',
                        height: '8px',
                        background: 'var(--accent-primary)',
                        borderRadius: '50%',
                        border: '1px solid white'
                      }} />
                    )}
                  </div>
                  <div style={{flex: 1, minWidth: 0}}>
                    <div className="file-name" style={{fontWeight: 500, fontSize: '15px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{file.name}</div>
                    <div style={{fontSize: '11px', color: 'var(--text-muted)'}}>
                      {file.type} • {file.sizeMB ? `${file.sizeMB}MB` : file.size ? `${Math.round(file.size / (1024*1024))}MB` : 'Unknown size'}
                    </div>
                  </div>
                  <div className="file-duration" style={{fontSize: '12px', color: 'var(--text-muted)', marginRight: '10px'}}>{file.duration}</div>
                  {/* Remove file button */}
                  <button
                    onClick={e => { e.stopPropagation(); handleRemoveFile(file.name); }}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                      padding: '4px',
                      borderRadius: '50%',
                      transition: 'background 0.15s',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                    title="Remove file"
                  >
                    <Trash2 style={{width: '16px', height: '16px'}} />
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))',
              gap: '12px'
            }}>
              {filteredFiles.map(file => (
                <div 
                  key={file.name} 
                  onClick={() => handleFileClick(file)}
                  style={{
                    background: 'var(--gradient-surface)',
                    border: '1px solid var(--border-primary)',
                    borderRadius: 'var(--radius-lg)',
                    padding: '16px 10px 12px 10px',
                    cursor: 'pointer',
                    transition: 'all var(--transition-normal)',
                    textAlign: 'center',
                    position: 'relative',
                    boxShadow: '0 1px 4px rgba(0,0,0,0.03)',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateY(-2px)';
                    e.currentTarget.style.boxShadow = 'var(--shadow-moderate)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                >
                  {/* Remove file button (top-right) */}
                  <button
                    onClick={e => { e.stopPropagation(); handleRemoveFile(file.name); }}
                    style={{
                      position: 'absolute',
                      top: '6px',
                      right: '6px',
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                      padding: '4px',
                      borderRadius: '50%',
                      transition: 'background 0.15s',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      zIndex: 2,
                    }}
                    title="Remove file"
                  >
                    <Trash2 style={{width: '15px', height: '15px'}} />
                  </button>
                  {file.type === 'image' && file.url ? (
                    <div style={{
                      width: '48px',
                      height: '48px',
                      borderRadius: 'var(--radius-md)',
                      margin: '0 auto 8px',
                      overflow: 'hidden',
                      background: 'var(--gradient-accent)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}>
                      <img 
                        src={file.url} 
                        alt={file.name}
                        style={{
                          width: '100%',
                          height: '100%',
                          objectFit: 'cover'
                        }}
                        onError={(e) => {
                          // Fallback to emoji if image fails to load
                          e.currentTarget.style.display = 'none';
                          e.currentTarget.parentElement!.innerHTML = '🖼️';
                          e.currentTarget.parentElement!.style.fontSize = '20px';
                        }}
                      />
                    </div>
                  ) : (
                    <div style={{
                      width: '48px',
                      height: '48px',
                      background: 'var(--gradient-accent)',
                      borderRadius: 'var(--radius-md)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      margin: '0 auto 8px',
                      fontSize: '20px'
                    }}>
                      {file.type === 'video' ? '🎬' : file.type === 'audio' ? '🎵' : '🖼️'}
                    </div>
                  )}
                  <div style={{
                    fontSize: '12px',
                    fontWeight: 500,
                    color: 'var(--text-primary)',
                    marginBottom: '4px',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap'
                  }}>
                    {file.name}
                  </div>
                  <div style={{
                    fontSize: '10px',
                    color: 'var(--text-muted)'
                  }}>
                    {file.type} • {Math.round(file.size / (1024*1024))}MB
                  </div>
                  <div style={{
                    fontSize: '10px',
                    color: 'var(--text-muted)'
                  }}>
                    {file.duration}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* File Upload Area */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={handleBrowseFiles}
          style={{
            marginTop: '16px',
            border: `2px dashed ${dragOver ? 'var(--accent-blue)' : 'var(--border-secondary)'}`,
            background: dragOver ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
            borderRadius: 'var(--radius-lg)',
            padding: '20px',
            textAlign: 'center',
            cursor: 'pointer',
            transition: 'all var(--transition-fast)'
          }}
          onMouseEnter={(e) => {
            if (!dragOver) {
              e.currentTarget.style.borderColor = 'var(--accent-blue)';
              e.currentTarget.style.background = 'rgba(59, 130, 246, 0.05)';
            }
          }}
          onMouseLeave={(e) => {
            if (!dragOver) {
              e.currentTarget.style.borderColor = 'var(--border-secondary)';
              e.currentTarget.style.background = 'transparent';
            }
          }}
        >
          <Upload style={{
            width: '24px',
            height: '24px',
            margin: '0 auto 8px',
            color: dragOver ? 'var(--accent-blue)' : 'var(--text-muted)'
          }} />
          <div style={{
            fontSize: '14px',
            fontWeight: 500,
            color: dragOver ? 'var(--accent-blue)' : 'var(--text-muted)',
            marginBottom: '4px'
          }}>
            {dragOver ? 'Drop files here' : 'Add Media Files'}
          </div>
          <div style={{
            fontSize: '12px',
            color: 'var(--text-muted)'
          }}>
            Drag & drop or click to browse
          </div>
        </div>
      </div>
    </div>
  );
};

const ProjectNavBar = () => (
  <div className="project-navbar" style={{
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    height: '44px', background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border-primary)',
    fontWeight: 600, fontSize: '1.1rem', letterSpacing: '0.02em', color: 'var(--text-primary)'
  }}>
    <span>Untitled Project</span>
  </div>
);

// Enhanced Video Preview Component
const VideoPreviewPanel = ({ selectedFile, onFileRemoved, onFileSelect }: { 
  selectedFile?: any, 
  onFileRemoved?: () => void,
  onFileSelect?: (file: any) => void 
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(0.8);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [mediaUrl, setMediaUrl] = useState<string | null>(null);
  const [showControls, setShowControls] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  
  // Get AI-generated videos from realtime store
  const videoPreviews = useRealtimeStore((s) => s.videoPreviews);
  const isProcessing = useRealtimeStore((s) => 
    s.toolCalls.some(call => call.tool === "video_processor")
  );
  
  // Get the latest AI-generated video
  const latestAIVideo = videoPreviews.length > 0 ? videoPreviews[videoPreviews.length - 1] : null;

  useEffect(() => {
    if (selectedFile) {
      let url: string | null = null;
      
      if (selectedFile.file) {
        // Handle uploaded files (with File object)
        url = URL.createObjectURL(selectedFile.file);
      } else if (selectedFile.url) {
        // Handle project files (with URL)
        url = selectedFile.url;
      }
      
      if (url) {
        setMediaUrl(url);
        
        // Reset state for new file
        setIsPlaying(false);
        setCurrentTime(0);
        setDuration(0);
        setIsLoading(true);

        return () => {
          // Only revoke URL if it was created with createObjectURL
          if (selectedFile.file) {
            URL.revokeObjectURL(url);
          }
          setMediaUrl(null);
        };
      }
    } else {
      // Clear state if no file is selected
      setMediaUrl(null);
      setIsPlaying(false);
      setCurrentTime(0);
      setDuration(0);
    }
  }, [selectedFile]);

  const formatTime = (seconds: number) => {
    if (!seconds || isNaN(seconds) || !isFinite(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getCurrentMediaElement = () => {
    if (selectedFile?.type === 'video') return videoRef.current;
    if (selectedFile?.type === 'audio') return audioRef.current;
    return null;
  };

  const handlePlayPause = async () => {
    const media = getCurrentMediaElement();
    if (!media) return;

    if (media.paused) {
      try {
        await media.play();
      } catch (error) {
        console.error('Error playing media:', error);
      }
    } else {
      media.pause();
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTime = Number(e.target.value);
    const media = getCurrentMediaElement();
    
    if (media && isFinite(media.duration)) {
      media.currentTime = newTime;
      setCurrentTime(newTime);
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = Number(e.target.value);
    setVolume(newVolume);
    const media = getCurrentMediaElement();
    if (media) {
      media.volume = newVolume;
    }
  };

  const handleFullscreen = async () => {
    if (!containerRef.current) return;

    try {
      if (!document.fullscreenElement) {
        await containerRef.current.requestFullscreen();
        setIsFullscreen(true);
      } else {
        await document.exitFullscreen();
        setIsFullscreen(false);
      }
    } catch (error) {
      console.error('Fullscreen error:', error);
    }
  };

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  useEffect(() => {
    let timeoutId: number;
    const handleMouseMove = () => {
      setShowControls(true);
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => setShowControls(false), 3000);
    };

    if (isFullscreen) {
      handleMouseMove(); // Show controls immediately on entering fullscreen
      window.addEventListener('mousemove', handleMouseMove);
    } else {
      setShowControls(false); // Hide controls when exiting fullscreen
    }

    return () => {
      clearTimeout(timeoutId);
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, [isFullscreen]);

  // Media event handlers with enhanced logging
  const handleLoadedMetadata = (e: React.SyntheticEvent<HTMLVideoElement | HTMLAudioElement, Event>) => {
    const media = e.target as HTMLVideoElement | HTMLAudioElement;
    const newDuration = media.duration;
    console.log(`EVENT: onLoadedMetadata - duration: ${newDuration}, readyState: ${media.readyState}`);
    if (newDuration && isFinite(newDuration)) {
      setDuration(newDuration);
    }
    media.volume = volume;
  };

  const handleDurationChange = (e: React.SyntheticEvent<HTMLVideoElement | HTMLAudioElement, Event>) => {
    const media = e.target as HTMLVideoElement | HTMLAudioElement;
    const newDuration = media.duration;
    console.log(`EVENT: onDurationChange - duration: ${newDuration}, readyState: ${media.readyState}`);
    if (newDuration && isFinite(newDuration)) {
      setDuration(newDuration);
    }
  };

  const handleTimeUpdate = (e: React.SyntheticEvent<HTMLVideoElement | HTMLAudioElement, Event>) => {
    const media = e.target as HTMLVideoElement | HTMLAudioElement;
    if (isFinite(media.currentTime)) {
      setCurrentTime(media.currentTime);
    }
  };

  const handlePlay = () => {
    console.log("EVENT: onPlay");
    setIsPlaying(true);
  };

  const handlePause = () => {
    console.log("EVENT: onPause");
    setIsPlaying(false);
  };

  const handleEnded = () => {
    setIsPlaying(false);
    if(getCurrentMediaElement()) {
      getCurrentMediaElement()!.currentTime = 0;
    }
  };
  const handleError = (e: React.SyntheticEvent<HTMLVideoElement | HTMLAudioElement, Event>) => {
    const media = e.target as HTMLMediaElement;
    console.error('Media Error:', media.error);
    setIsLoading(false);
  };
  const handleCanPlay = () => {
    console.log("EVENT: onCanPlay");
    setIsLoading(false);
  };


  return (
    <div className="panel-content-wrapper">
      <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>🎥 Video Preview</span>
        {isProcessing && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            color: '#4facfe',
            fontSize: '12px'
          }}>
            <div style={{ 
              width: 12, 
              height: 12, 
              border: "2px solid #4facfe", 
              borderTop: "2px solid transparent", 
              borderRadius: "50%", 
              animation: "spin 1s linear infinite",
              marginRight: 6 
            }}></div>
            AI processing video...
          </div>
        )}
      </div>
      
      <div className="tab-content-area" style={{
        display: 'flex', 
        flexDirection: 'column',
        gap: '16px'
      }}>
        {/* Media Display Area */}
        <div 
          ref={containerRef}
          style={{
            flex: 1,
            background: '#000',
            borderRadius: 'var(--radius-lg)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            position: 'relative',
            minHeight: '200px',
            aspectRatio: '16/9',
            overflow: 'hidden'
          }}>
          {selectedFile && mediaUrl ? (
            <>
              {selectedFile.type === 'video' && (
                <video
                  key={mediaUrl}
                  ref={videoRef}
                  src={mediaUrl}
                  style={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'contain'
                  }}
                  onLoadedMetadata={handleLoadedMetadata}
                  onDurationChange={handleDurationChange}
                  onTimeUpdate={handleTimeUpdate}
                  onPlay={handlePlay}
                  onPause={handlePause}
                  onEnded={handleEnded}
                  onError={handleError}
                  onCanPlay={handleCanPlay}
                  onWaiting={() => setIsLoading(true)}
                  onPlaying={() => setIsLoading(false)}
                  preload="metadata"
                  playsInline
                />
              )}
              
              {selectedFile.type === 'audio' && (
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'white',
                  textAlign: 'center',
                  width: '100%',
                  height: '100%'
                }}>
                  <audio
                    key={mediaUrl}
                    ref={audioRef}
                    src={mediaUrl}
                    onLoadedMetadata={handleLoadedMetadata}
                    onDurationChange={handleDurationChange}
                    onTimeUpdate={handleTimeUpdate}
                    onPlay={handlePlay}
                    onPause={handlePause}
                    onEnded={handleEnded}
                    onError={handleError}
                    onCanPlay={handleCanPlay}
                    preload="metadata"
                  />
                  <div style={{
                    width: '80px',
                    height: '80px',
                    background: 'var(--gradient-accent)',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: '16px',
                    fontSize: '32px'
                  }}>
                    🎵
                  </div>
                  <div style={{fontSize: '18px', fontWeight: 600, marginBottom: '8px'}}>
                    {selectedFile.name}
                  </div>
                  <div style={{fontSize: '14px', opacity: 0.7}}>
                    Audio File • {Math.round(selectedFile.size / (1024*1024))}MB
                  </div>
                </div>
              )}
              
              {selectedFile.type === 'image' && (
                <img
                  src={mediaUrl}
                  alt={selectedFile.name}
                  style={{
                    maxWidth: '100%',
                    maxHeight: '100%',
                    objectFit: 'contain'
                  }}
                />
              )}
              
              {isLoading && selectedFile.type !== 'image' && (
                <div style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  background: 'rgba(0, 0, 0, 0.5)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'white',
                  fontSize: '18px'
                }}>
                  Loading...
                </div>
              )}
            </>
          ) : (
            <div style={{ padding: '20px', textAlign: 'center' }}>
              {latestAIVideo ? (
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '16px'
                }}>
                  <div style={{
                    width: '80px',
                    height: '80px',
                    background: 'linear-gradient(135deg, #51cf66 0%, #40c057 100%)',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '32px'
                  }}>
                    ✅
                  </div>
                  <div style={{ color: 'white', fontSize: '16px', fontWeight: 600 }}>
                    AI Video Ready!
                  </div>
                  <div style={{ color: '#888', fontSize: '14px' }}>
                    Your AI-generated video is complete
                  </div>
                  <button
                    onClick={() => {
                      // Set the AI video as selected
                      if (onFileSelect) {
                        onFileSelect({
                          ...latestAIVideo,
                          name: 'AI Generated Video',
                          type: 'video',
                          size: 0
                        });
                      }
                    }}
                    style={{
                      padding: '12px 24px',
                      background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
                      border: 'none',
                      borderRadius: '8px',
                      color: 'white',
                      cursor: 'pointer',
                      fontSize: '14px',
                      fontWeight: 600
                    }}
                  >
                    🎬 Play AI Video
                  </button>
                </div>
          ) : (
            <div className="video-preview-placeholder" style={{
              color: 'var(--text-muted)', 
              fontSize: '16px',
              fontWeight: 500,
              textAlign: 'center',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              opacity: 0.6
            }}>
              <div style={{
                width: '60px',
                height: '60px',
                background: 'var(--gradient-accent)',
                borderRadius: 'var(--radius-xl)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '12px',
                boxShadow: 'var(--shadow-glow)',
                cursor: 'pointer'
              }}>
                <Play style={{width: '24px', height: '24px', color: 'white'}} />
              </div>
              <div style={{fontSize: '14px', fontWeight: 600, marginBottom: '4px'}}>
                No Media Selected
              </div>
              <div style={{fontSize: '12px', opacity: 0.7}}>
                    Click a file to preview or wait for AI to generate a video
              </div>
                </div>
              )}
            </div>
          )}

          {/* Fullscreen Button */}
          {selectedFile && (
            <button
              onClick={handleFullscreen}
              style={{
                position: 'absolute',
                top: '12px',
                right: '12px',
                background: 'rgba(0, 0, 0, 0.7)',
                border: 'none',
                borderRadius: 'var(--radius-sm)',
                padding: '6px',
                color: 'white',
                cursor: 'pointer',
                transition: 'opacity 0.3s ease',
                opacity: isFullscreen && !showControls ? 0 : 1,
                zIndex: 2,
              }}
            >
              {isFullscreen ? 
                <Minimize2 style={{width: '16px', height: '16px'}} /> : 
                <Maximize2 style={{width: '16px', height: '16px'}} />
              }
            </button>
          )}

          {/* Media Controls Overlay */}
          <div style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            background: 'linear-gradient(to top, rgba(0,0,0,0.7), transparent)',
            padding: '16px',
            opacity: (!isFullscreen || showControls) && (selectedFile?.type === 'video' || selectedFile?.type === 'audio') ? 1 : 0,
            visibility: (!isFullscreen || showControls) && (selectedFile?.type === 'video' || selectedFile?.type === 'audio') ? 'visible' : 'hidden',
            transition: 'opacity 0.3s, visibility 0.3s',
            zIndex: 1,
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: '12px',
              color: 'white',
              textShadow: '0 1px 2px rgba(0,0,0,0.5)',
              marginBottom: '8px'
            }}>
              <span>{formatTime(currentTime)}</span>
              <span>{formatTime(duration)}</span>
            </div>
            <input type="range" min="0" max={duration || 0} value={currentTime || 0} onChange={handleSeek} disabled={!isFinite(duration) || duration === 0} style={{ width: '100%', cursor: 'pointer', marginBottom: '10px' }} />
            
            {/* Control Buttons */}
            <div style={{display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
              <button onClick={handlePlayPause} disabled={!selectedFile || isLoading} style={{
                  background: 'none',
                  border: 'none',
                  color: 'white',
                  cursor: 'pointer',
                  padding: 0
              }}>
                {isLoading ? <Loader size={32} className="animate-spin" /> : isPlaying ? <PauseCircle size={36} /> : <PlayCircle size={36} />}
              </button>
            </div>
          </div>
        </div>

        {/* Debug Info */}
        <div style={{
          fontSize: '10px',
          color: 'var(--text-muted)',
          fontFamily: 'monospace',
          background: 'var(--bg-secondary)',
          padding: '8px 12px',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-primary)'
        }}>
          Debug: Playing: {isPlaying.toString()}, Duration: {duration.toFixed(2)}s, Current: {currentTime.toFixed(2)}s, Loading: {isLoading.toString()}
        </div>
      </div>
    </div>
  );
};

// Add a thin navigation bar above the project name
const TopNavBar = () => (
  <div className="top-navbar" style={{
    height: '28px', background: 'var(--bg-tertiary)', borderBottom: '1px solid var(--border-secondary)',
    display: 'flex', alignItems: 'center', padding: '0 16px', fontSize: 13, color: 'var(--text-secondary)', fontWeight: 500, letterSpacing: '0.01em'
  }}>
    <span style={{fontWeight: 700, color: 'var(--accent-blue)', marginRight: 18}}>Sclip</span>
    <span style={{marginRight: 16, cursor: 'pointer'}}>File</span>
    <span style={{marginRight: 16, cursor: 'pointer'}}>Edit</span>
    <span style={{marginRight: 16, cursor: 'pointer'}}>View</span>
  </div>
);

const ScriptVoicesPanel = () => {
  const { addTag } = useSelectedTags();
  const [tab, setTab] = useState<'script'|'voices'>('script');
  const [selectedVoice, setSelectedVoice] = useState<string | null>(null);
  const [playingVoice, setPlayingVoice] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Get script from realtime store
  const script = useRealtimeStore((s) => {
    // First try to get from toolResults
    const scriptResult = [...s.toolResults].reverse().find(
      (msg) => msg.tool === "script_writer" && msg.result?.script_text
    );
    
    if (scriptResult?.result?.script_text) {
      console.log("Found script in toolResults:", scriptResult.result.script_text.substring(0, 100));
      return scriptResult.result.script_text;
    }
    
    // Fallback to scripts array
    if (s.scripts.length > 0) {
      const latestScript = s.scripts[s.scripts.length - 1];
      console.log("Found script in scripts array:", latestScript.content.substring(0, 100));
      return latestScript.content;
    }
    
    return mockScript; // Fallback to mock script if no real script
  });
  
  const scripts = useRealtimeStore((s) => s.scripts);
  const toolResults = useRealtimeStore((s) => s.toolResults);
  const isGenerating = useRealtimeStore((s) => 
    s.toolCalls.some(call => call.tool === "script_writer")
  );
  
  // Debug logging
  console.log("ScriptVoicesPanel - script:", script ? script.substring(0, 100) + "..." : "No script");
  console.log("ScriptVoicesPanel - scripts array length:", scripts.length);
  console.log("ScriptVoicesPanel - toolResults length:", toolResults.length);
  console.log("ScriptVoicesPanel - toolResults:", toolResults.map(tr => ({ tool: tr.tool, hasScript: !!tr.result?.script_text })));
  
  // Local state for editing
  const [editValue, setEditValue] = useState(script);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  
  // Update editValue when script changes
  useEffect(() => { 
    if (script && script !== editValue) {
      console.log("Updating editValue with new script");
      setEditValue(script); 
    }
  }, [script, editValue]);
  
  // Get sessionId for updates
  const sessionId = useRealtimeStore((s) => {
    const last = [...s.messages].reverse().find((m) => m.session_id);
    return last?.session_id || "";
  });

  // Clear any existing script files from project files on mount
  const clearScriptFiles = useRealtimeStore((s) => s.clearScriptFiles);
  useEffect(() => {
    clearScriptFiles();
  }, [clearScriptFiles]);

  // Send script updates to backend
  const sendScriptUpdate = async (scriptContent: string) => {
    if (!sessionId) return;
    
    try {
      const response = await fetch(`http://localhost:8000/api/update-script`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          script_content: scriptContent
        })
      });
      
      if (!response.ok) {
        console.error('Failed to update script on backend');
      }
    } catch (error) {
      console.error('Error sending script update:', error);
    }
  };

  // Debounced script update
  const debouncedScriptUpdate = useRef<ReturnType<typeof setTimeout>>();
  useEffect(() => {
    if (debouncedScriptUpdate.current) {
      clearTimeout(debouncedScriptUpdate.current);
    }
    
    if (editValue && editValue !== script) {
      debouncedScriptUpdate.current = setTimeout(() => {
        sendScriptUpdate(editValue);
      }, 1000); // Wait 1 second after user stops typing
    }
    
    return () => {
      if (debouncedScriptUpdate.current) {
        clearTimeout(debouncedScriptUpdate.current);
      }
    };
  }, [editValue, script, sessionId]);

  // Helper to get preview file path for a voice
  const getPreviewPath = (voiceName: string) => {
    // Convert e.g. en-US-Neural2-A to en-US-Neural2-A
    return `/resources/preview_cache/voice_${voiceName}.mp3`;
  };

  // Stop and clean up audio
  const stopAudio = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current = null;
    }
    setPlayingVoice(null);
  };

  // Play preview for a given voice
  const handleVoicePreview = (voice: any) => {
    if (playingVoice === voice.name) {
      stopAudio();
      return;
    }
    stopAudio();
    const audioSrc = getPreviewPath(voice.name);
    const audio = new window.Audio(audioSrc);
    audioRef.current = audio;
    setPlayingVoice(voice.name);
    audio.onplay = () => {
      console.log(`[Voice Preview] Playing: ${voice.name} (${audioSrc})`);
    };
    audio.onended = () => {
      console.log(`[Voice Preview] Ended: ${voice.name}`);
      setPlayingVoice(null);
      audioRef.current = null;
    };
    audio.onerror = (e) => {
      console.error(`[Voice Preview] Error loading/playing: ${voice.name} (${audioSrc})`, e);
      setPlayingVoice(null);
      audioRef.current = null;
    };
    audio.play().catch(err => {
      console.error(`[Voice Preview] Play promise rejected: ${voice.name} (${audioSrc})`, err);
      setPlayingVoice(null);
      audioRef.current = null;
    });
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopAudio();
    };
  }, []);

  async function handleSave() {
    if (!sessionId) return;
    setSaving(true);
    setSaved(false);
    // TODO: Implement real backend call
    await new Promise((res) => setTimeout(res, 500));
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 1200);
  }

  return (
    <div className="panel-content-wrapper">
      <div className="modern-tabs">
        <button 
          onClick={() => setTab('script')} 
          className={`modern-tab ${tab === 'script' ? 'active' : ''}`}
        >
          <FileText style={{width: '16px', height: '16px', marginRight: '6px'}} />
          Script
        </button>
        <button 
          onClick={() => setTab('voices')} 
          className={`modern-tab ${tab === 'voices' ? 'active' : ''}`}
        >
          <Mic style={{width: '16px', height: '16px', marginRight: '6px'}} />
          Voices
        </button>
      </div>
      <div className="tab-content-area">
        {tab === 'script' ? (
          <div style={{height: '100%', display: 'flex', flexDirection: 'column'}}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <label style={{
              fontSize: '14px',
              fontWeight: 600,
              color: 'var(--text-secondary)',
              display: 'block'
            }}>
              Video Script
            </label>
              {isGenerating && (
                <div style={{ display: "flex", alignItems: "center", color: "#4facfe", fontSize: "12px" }}>
                  <div style={{ 
                    width: 12, 
                    height: 12, 
                    border: "2px solid #4facfe", 
                    borderTop: "2px solid transparent", 
                    borderRadius: "50%", 
                    animation: "spin 1s linear infinite",
                    marginRight: 6 
                  }}></div>
                  AI is generating script...
                </div>
              )}
            </div>
            
            {editValue && editValue !== mockScript && (
              <div style={{ 
                marginBottom: 8, 
                padding: "6px 10px", 
                background: "linear-gradient(135deg, #51cf66 0%, #40c057 100%)", 
                borderRadius: "6px", 
                color: "white", 
                fontSize: "11px",
                display: "flex",
                alignItems: "center",
                gap: "6px"
              }}>
                <span>✅</span>
                <span>Script loaded successfully! You can edit it below.</span>
              </div>
            )}
            
            <textarea 
              className="script-editor" 
              value={editValue} 
              onChange={e => setEditValue(e.target.value)} 
              placeholder={editValue && editValue !== mockScript ? "Edit your script here..." : "AI will generate your script here as it works..."}
            />
            
            {editValue && editValue !== mockScript && (
              <div style={{ marginTop: 8, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <button 
                    onClick={handleSave} 
                    disabled={saving}
                    style={{
                      padding: "6px 12px",
                      background: saving ? "#666" : "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)",
                      border: "none",
                      borderRadius: "4px",
                      color: "white",
                      cursor: saving ? "not-allowed" : "pointer",
                      fontSize: "12px"
                    }}
                  >
                    {saving ? "Saving..." : "Save Script"}
                  </button>
                  {saved && (
                    <span style={{ color: "#51cf66", marginLeft: 6, fontSize: "11px" }}>
                      ✅ Saved!
                    </span>
                  )}
                </div>
                
                <div style={{ color: "#888", fontSize: "10px" }}>
                  {editValue.split('\n').length} lines • {editValue.length} characters
                </div>
              </div>
            )}
          </div>
        ) : (
          <div style={{height: '100%', display: 'flex', flexDirection: 'column'}}>
            <label style={{
              fontSize: '14px',
              fontWeight: 600,
              color: 'var(--text-secondary)',
              marginBottom: '16px',
              display: 'block'
            }}>
              English AI Voice Selection
            </label>
            <div style={{
              fontSize: '12px',
              color: 'var(--text-muted)',
              marginBottom: '12px'
            }}>
              Select from {englishVoices.length} premium English voices across Neural2, Wavenet, and Standard libraries
            </div>
            <div className="gallery-grid" style={{
              display: 'grid', 
              gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', 
              gap: '12px'
            }}>
            {englishVoices.map(voice => (
                <div 
                  className="gallery-item" 
                  key={voice.name}
                  onClick={() => {
                    setSelectedVoice(voice.name);
                    addTag({
                      id: voice.name,
                      name: voice.name,
                      type: 'voice',
                      displayName: `${voice.displayName} (${voice.accent})`
                    });
                  }}
                  style={{
                    background: selectedVoice === voice.name ? 'var(--gradient-accent)' : 'var(--gradient-surface)',
                    border: selectedVoice === voice.name ? '1px solid var(--accent-blue)' : '1px solid var(--border-primary)',
                    borderRadius: 'var(--radius-lg)',
                    padding: '12px',
                    cursor: 'pointer',
                    transition: 'all var(--transition-normal)',
                    fontSize: '12px',
                    fontWeight: 500,
                    textAlign: 'center',
                    minHeight: '100px',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    position: 'relative',
                    overflow: 'hidden'
                  }}
                >
                  <div style={{flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
                    <User style={{
                      width: '18px', 
                      height: '18px', 
                      marginBottom: '4px', 
                      opacity: 0.7,
                      color: voice.gender === 'Female' ? '#ff6b9d' : '#4dabf7'
                    }} />
                    <div style={{fontWeight: 600, marginBottom: '2px'}}>{voice.displayName}</div>
                    <div style={{fontSize: '10px', opacity: 0.7, marginBottom: '2px'}}>{voice.accent} • {voice.gender}</div>
                    <div style={{
                      fontSize: '9px', 
                      opacity: 0.6,
                      background: voice.technology === 'Neural2' ? '#4c956c' : voice.technology === 'Wavenet' ? '#f2994a' : '#95a5a6',
                      color: 'white',
                      padding: '1px 4px',
                      borderRadius: '3px'
                    }}>
                      {voice.technology}
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleVoicePreview(voice);
                    }}
                    style={{
                      background: playingVoice === voice.name ? 'var(--gradient-accent)' : 'var(--bg-tertiary)',
                      border: '1px solid var(--border-primary)',
                      borderRadius: '50%',
                      width: '24px',
                      height: '24px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      cursor: 'pointer',
                      marginTop: '8px',
                      transition: 'all var(--transition-normal)'
                    }}
                  >
                    {playingVoice === voice.name ? 
                      <Pause style={{width: '10px', height: '10px', color: 'white'}} /> :
                      <Play style={{width: '10px', height: '10px', color: 'var(--text-primary)'}} />
                    }
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const EffectsTransitionsFiltersPanel = () => {
  const { addTag } = useSelectedTags();
  const [tab, setTab] = useState<'effects' | 'transitions' | 'filters'>('effects');
  const [effects, setEffects] = useState<Asset[]>([]);
  const [filters, setFilters] = useState<Asset[]>([]);
  const [transitions, setTransitions] = useState<Asset[]>([]);
  const [loadingError, setLoadingError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAssets = async () => {
      try {
        setLoadingError(null);
        const [effectsRes, filtersRes, transitionsRes] = await Promise.all([
                  fetch('http://127.0.0.1:8001/assets/effects'),
        fetch('http://127.0.0.1:8001/assets/filters'),
        fetch('http://127.0.0.1:8001/assets/transitions'),
        ]);
        if (!effectsRes.ok || !filtersRes.ok || !transitionsRes.ok) {
          throw new Error('Failed to fetch assets');
        }
        const effectsData = await effectsRes.json();
        const filtersData = await filtersRes.json();
        const transitionsData = await transitionsRes.json();
        setEffects(effectsData.effects || []);
        setFilters(filtersData.filters || []);
        setTransitions(transitionsData.transitions || []);
      } catch (error) {
        console.error("Asset loading error:", error);
        console.error("Error details:", {
          message: error instanceof Error ? error.message : 'Unknown error',
          stack: error instanceof Error ? error.stack : undefined
        });
        setLoadingError("Could not load assets. Is the sidecar running?");
      }
    };
    fetchAssets();
  }, []);

  const getTabIcon = (tabName: string) => {
    switch (tabName) {
      case 'effects': return <Wand2 style={{ width: '16px', height: '16px', marginRight: '6px' }} />;
      case 'transitions': return <Layers style={{ width: '16px', height: '16px', marginRight: '6px' }} />;
      case 'filters': return <Palette style={{ width: '16px', height: '16px', marginRight: '6px' }} />;
      default: return null;
    }
  };

  // Lazy Image Component
  const LazyImage = ({ src, alt }: { src: string; alt: string }) => {
    const [isLoaded, setIsLoaded] = useState(false);
    const [isInView, setIsInView] = useState(false);
    const [hasError, setHasError] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
      const observer = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting) {
            setIsInView(true);
            observer.disconnect();
          }
        },
        { threshold: 0.1 }
      );

      if (containerRef.current) {
        observer.observe(containerRef.current);
      }

      return () => observer.disconnect();
    }, []);

    const handleLoad = () => {
      setIsLoaded(true);
      setHasError(false);
    };

    const handleError = () => {
      setHasError(true);
      setIsLoaded(false);
    };

    return (
      <div 
        ref={containerRef} 
        style={{ 
          width: 64, 
          height: 64, 
          background: 'var(--bg-secondary)', 
          borderRadius: 8,
          position: 'relative',
          overflow: 'hidden'
        }}
      >
        {isInView && !hasError && (
          <img
            src={src}
            alt={alt}
            onLoad={handleLoad}
            onError={handleError}
            style={{
              width: 64,
              height: 64,
              objectFit: 'cover',
              borderRadius: 8,
              boxShadow: '0 2px 8px #0002',
              opacity: isLoaded ? 1 : 0,
              transition: 'opacity 0.3s ease'
            }}
          />
        )}
        {isInView && !isLoaded && !hasError && (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: 64,
              height: 64,
              background: 'var(--bg-tertiary)',
              borderRadius: 8,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 10,
              color: 'var(--text-muted)'
            }}
          >
            ⏳
          </div>
        )}
        {hasError && (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: 64,
              height: 64,
              background: 'var(--bg-tertiary)',
              borderRadius: 8,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 10,
              color: 'var(--text-muted)'
            }}
          >
            ❌
          </div>
        )}
      </div>
    );
  };

  const renderAssetGrid = (assets: Asset[], icon: React.ReactNode) => (
    <div className="gallery-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(110px, 1fr))', gap: '12px' }}>
      {assets.map(asset => {
        let imgUrl = '';
        let mediaType = 'image/jpeg';
        
        if (tab === 'effects') {
                      imgUrl = `http://127.0.0.1:8001/preview/effect/${asset.id}`;
          mediaType = 'image/gif';
        }
        if (tab === 'filters') {
                      imgUrl = `http://127.0.0.1:8001/preview/filter/${asset.id}`;
          mediaType = 'image/jpeg';
        }
        if (tab === 'transitions') {
                      imgUrl = `http://127.0.0.1:8001/preview/transition/${asset.id}`;
          mediaType = 'image/gif';
        }

        return (
          <div
            className="gallery-item"
            key={asset.id}
            onClick={() => {
              addTag({
                id: asset.id,
                name: asset.name,
                type: tab as 'effect' | 'filter' | 'transition',
                displayName: asset.name
              });
            }}
            style={{
              background: 'var(--gradient-surface)',
              border: '1px solid var(--border-primary)',
              borderRadius: 'var(--radius-lg)',
              padding: '8px',
              cursor: 'pointer',
              transition: 'all var(--transition-normal)',
              fontSize: '12px',
              fontWeight: 500,
              textAlign: 'center',
              minHeight: '110px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'flex-start',
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            <div style={{ position: 'relative', width: 64, height: 64, marginBottom: 8 }}>
              <LazyImage
                src={imgUrl}
                alt={asset.name}
              />
              <div style={{ position: 'absolute', top: 4, right: 4, opacity: 0.7 }}>{icon}</div>
            </div>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', width: 80 }}>
              {asset.name}
            </div>
          </div>
        );
      })}
    </div>
  );

  return (
    <div className="panel-content-wrapper">
      <div className="modern-tabs">
        <button
          onClick={() => setTab('effects')}
          className={`modern-tab ${tab === 'effects' ? 'active' : ''}`}
        >
          {getTabIcon('effects')}
          Effects
        </button>
        <button
          onClick={() => setTab('transitions')}
          className={`modern-tab ${tab === 'transitions' ? 'active' : ''}`}
        >
          {getTabIcon('transitions')}
          Transitions
        </button>
        <button
          onClick={() => setTab('filters')}
          className={`modern-tab ${tab === 'filters' ? 'active' : ''}`}
        >
          {getTabIcon('filters')}
          Filters
        </button>
      </div>
      <div className="tab-content-area">
        {loadingError ? (
          <div className="asset-error-message" style={{padding: '20px', textAlign: 'center'}}>
            <AlertCircle className="w-5 h-5 text-yellow-400" style={{margin: '0 auto 8px', display: 'block'}} />
            <p>{loadingError}</p>
          </div>
        ) : (
          <>
            {tab === 'effects' && (
              <div>
                <label style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '16px', display: 'block' }}>
                  Animated Effects (GIFs)
                </label>
                {renderAssetGrid(effects, <Sparkles />)}
              </div>
            )}
            {tab === 'transitions' && (
              <div>
                <label style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '16px', display: 'block' }}>
                  Scene Transitions (GIFs)
                </label>
                {renderAssetGrid(transitions, <Layers />)}
              </div>
            )}
            {tab === 'filters' && (
              <div>
                <label style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '16px', display: 'block' }}>
                  Visual Filters (Static Images)
                </label>
                {renderAssetGrid(filters, <Palette />)}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

// Professional Toolbar Component
const ProfessionalToolbar = () => {
  const [undoStack, setUndoStack] = useState(0);
  const [redoStack, setRedoStack] = useState(0);

  return (
    <div style={{
      background: 'var(--gradient-surface)',
      borderBottom: '1px solid var(--border-primary)',
      padding: '8px 16px',
      display: 'flex',
      alignItems: 'center',
      gap: '16px',
      flexShrink: 0,
      height: '48px'
    }}>
      {/* Edit Tools */}
      <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
        <button
          className="toolbar-undo-redo-btn"
          style={{
            background: undoStack > 0 ? 'var(--bg-tertiary)' : 'var(--bg-secondary)',
            border: '1px solid var(--border-primary)',
            borderRadius: 'var(--radius-md)',
            padding: '6px 8px',
            color: undoStack > 0 ? 'var(--text-primary)' : 'var(--text-disabled)',
            cursor: undoStack > 0 ? 'pointer' : 'not-allowed',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '13px',
            fontWeight: 500
          }}
          disabled={undoStack === 0}
          title="Undo (Ctrl+Z)"
        >
          <Undo style={{width: '14px', height: '14px'}} />
          Undo
        </button>

        <button
          className="toolbar-undo-redo-btn"
          style={{
            background: redoStack > 0 ? 'var(--bg-tertiary)' : 'var(--bg-secondary)',
            border: '1px solid var(--border-primary)',
            borderRadius: 'var(--radius-md)',
            padding: '6px 8px',
            color: redoStack > 0 ? 'var(--text-primary)' : 'var(--text-disabled)',
            cursor: redoStack > 0 ? 'pointer' : 'not-allowed',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '13px',
            fontWeight: 500
          }}
          disabled={redoStack === 0}
          title="Redo (Ctrl+Y)"
        >
          <Redo style={{width: '14px', height: '14px'}} />
          Redo
        </button>
    </div>

      {/* Divider */}
      <div style={{width: '1px', height: '24px', background: 'var(--border-primary)'}}></div>

      {/* Clipboard Tools */}
      <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
        <button
          style={{
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-primary)',
            borderRadius: 'var(--radius-md)',
            padding: '6px 8px',
            color: 'var(--text-primary)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '13px',
            fontWeight: 500
          }}
          title="Cut (Ctrl+X)"
        >
          <Scissors style={{width: '14px', height: '14px'}} />
          Cut
        </button>

        <button
          style={{
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-primary)',
            borderRadius: 'var(--radius-md)',
            padding: '6px 8px',
            color: 'var(--text-primary)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '13px',
            fontWeight: 500
          }}
          title="Copy (Ctrl+C)"
        >
          <Copy style={{width: '14px', height: '14px'}} />
          Copy
        </button>

        <button
          style={{
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-primary)',
            borderRadius: 'var(--radius-md)',
            padding: '6px 8px',
            color: 'var(--text-primary)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '13px',
            fontWeight: 500
          }}
          title="Delete (Del)"
        >
          <Trash2 style={{width: '14px', height: '14px'}} />
          Delete
        </button>
    </div>

      {/* Divider */}
      <div style={{width: '1px', height: '24px', background: 'var(--border-primary)'}}></div>

      {/* Transform Tools */}
      <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
        <button
          style={{
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-primary)',
            borderRadius: 'var(--radius-md)',
            padding: '6px',
            color: 'var(--text-primary)',
            cursor: 'pointer'
          }}
          title="Zoom In"
        >
          <ZoomIn style={{width: '14px', height: '14px'}} />
        </button>

        <button
          style={{
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-primary)',
            borderRadius: 'var(--radius-md)',
            padding: '6px',
            color: 'var(--text-primary)',
            cursor: 'pointer'
          }}
          title="Zoom Out"
        >
          <ZoomOut style={{width: '14px', height: '14px'}} />
        </button>

        <button
          style={{
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-primary)',
            borderRadius: 'var(--radius-md)',
            padding: '6px',
            color: 'var(--text-primary)',
            cursor: 'pointer'
          }}
          title="Split Clip"
        >
          <Split style={{width: '14px', height: '14px'}} />
        </button>
    </div>

      {/* Right Side - Export & Settings */}
      <div style={{marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '12px'}}>
        {/* Quick Export */}
        <button
          style={{
            background: 'var(--gradient-accent)',
            border: 'none',
            borderRadius: 'var(--radius-md)',
            padding: '8px 16px',
            color: 'white',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '13px',
            fontWeight: 600,
            boxShadow: 'var(--shadow-moderate)'
          }}
          title="Quick Export"
        >
          <Download style={{width: '14px', height: '14px'}} />
          Export
        </button>

        {/* Project Settings */}
        <button
          style={{
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-primary)',
            borderRadius: 'var(--radius-md)',
            padding: '6px',
            color: 'var(--text-primary)',
            cursor: 'pointer'
          }}
          title="Project Settings"
        >
          <Settings style={{width: '16px', height: '16px'}} />
        </button>

        {/* Keyboard Shortcuts */}
        <button
          style={{
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-primary)',
            borderRadius: 'var(--radius-md)',
            padding: '6px',
            color: 'var(--text-primary)',
            cursor: 'pointer'
          }}
          title="Keyboard Shortcuts"
        >
          <Lightbulb style={{width: '16px', height: '16px'}} />
        </button>
      </div>
    </div>
  );
};

// Advanced Panel Management Component
const PanelManager = ({ children, title, onMinimize, onMaximize, onClose, isResizable = true }: {
  children: React.ReactNode;
  title: string;
  onMinimize?: () => void;
  onMaximize?: () => void;
  onClose?: () => void;
  isResizable?: boolean;
}) => {
  const [isMinimized, setIsMinimized] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const handleMinimize = () => {
    setIsMinimized(!isMinimized);
    onMinimize?.();
  };

  const handleMaximize = () => {
    setIsMaximized(!isMaximized);
    onMaximize?.();
  };

  return (
    <div className={`resizable-panel ${isMaximized ? 'panel-maximized' : ''} ${isMinimized ? 'panel-minimized' : ''}`}>
      {/* Panel Controls */}
      <div className="panel-controls">
            <button
          className="panel-control-btn"
          onClick={handleMinimize}
          title={isMinimized ? "Restore" : "Minimize"}
        >
          {isMinimized ? <Square style={{width: '12px', height: '12px'}} /> : <Minus style={{width: '12px', height: '12px'}} />}
        </button>
        <button
          className="panel-control-btn"
          onClick={handleMaximize}
          title={isMaximized ? "Restore" : "Maximize"}
        >
          <Maximize2 style={{width: '12px', height: '12px'}} />
        </button>
        {onClose && (
          <button
            className="panel-control-btn"
            onClick={onClose}
            title="Close Panel"
          >
            <X style={{width: '12px', height: '12px'}} />
          </button>
        )}
      </div>

      {/* Resize Handles */}
      {isResizable && !isMaximized && (
        <>
          <div className="resize-handle resize-handle-right"></div>
          <div className="resize-handle resize-handle-bottom"></div>
          <div className="resize-handle resize-handle-corner"></div>
        </>
      )}

      {children}
    </div>
  );
};

// Workspace Layout Manager
const WorkspaceLayoutManager = ({ currentLayout, onLayoutChange }: {
  currentLayout: string;
  onLayoutChange: (layout: string) => void;
}) => {
  const layouts = [
    { id: 'default', name: 'Default', icon: '⊞' },
    { id: 'focus', name: 'Focus', icon: '⊠' },
    { id: 'timeline', name: 'Timeline', icon: '━' },
    { id: 'preview', name: 'Preview', icon: '▶' }
  ];

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      padding: '8px 16px',
      background: 'var(--gradient-surface)',
      borderBottom: '1px solid var(--border-primary)'
    }}>
      <span style={{
        fontSize: '12px',
        fontWeight: 600,
        color: 'var(--text-muted)',
        textTransform: 'uppercase',
        letterSpacing: '0.5px'
      }}>
        Layout:
      </span>
      <div className="layout-switcher">
        {layouts.map(layout => (
          <button
            key={layout.id}
            className={`layout-option ${currentLayout === layout.id ? 'active' : ''}`}
            onClick={() => onLayoutChange(layout.id)}
            title={layout.name}
          >
            <span style={{fontSize: '16px'}}>{layout.icon}</span>
          </button>
        ))}
      </div>
      
      <div style={{marginLeft: 'auto', display: 'flex', gap: '8px', alignItems: 'center'}}>
        <button style={{
          background: 'var(--bg-tertiary)',
          border: '1px solid var(--border-primary)',
          borderRadius: 'var(--radius-sm)',
          padding: '4px 8px',
          color: 'var(--text-secondary)',
          fontSize: '11px',
          cursor: 'pointer'
        }}>
          <Save style={{width: '12px', height: '12px', marginRight: '4px'}} />
          Save Layout
        </button>
        <button style={{
          background: 'var(--bg-tertiary)',
          border: '1px solid var(--border-primary)',
          borderRadius: 'var(--radius-sm)',
          padding: '4px 8px',
          color: 'var(--text-secondary)',
          fontSize: '11px',
          cursor: 'pointer'
        }}>
          <RotateCcw style={{width: '12px', height: '12px', marginRight: '4px'}} />
          Reset
        </button>
      </div>
    </div>
  );
};

// Enhanced Main Editor with corrected 2x2 Grid
const MainEditorGrid = ({ currentProject }: { currentProject?: any }) => {
  const [selectedFile, setSelectedFile] = useState<any>(null);

  const handleFileSelect = (file: any) => {
    setSelectedFile(file);
  };

  const handleFileRemoved = () => {
    setSelectedFile(null);
  };

  return (
    <div className="main-editor-grid">
      <div className="floating-panel">
        <FilesPanel 
          onFileSelect={handleFileSelect} 
          selectedFile={selectedFile} 
          onFileRemoved={handleFileRemoved}
          currentProject={currentProject}
        />
      </div>
      <div className="floating-panel">
        <VideoPreviewPanel selectedFile={selectedFile} onFileSelect={handleFileSelect} onFileRemoved={handleFileRemoved} />
      </div>
      <div className="floating-panel">
      <EffectsTransitionsFiltersPanel />
    </div>
      <div className="floating-panel">
        <ScriptVoicesPanel />
    </div>
  </div>
);
};

// Professional Status Bar Component
const StatusBar = () => {
  const [projectInfo] = useState({
    name: 'Untitled Project',
    duration: '2:47',
    size: '245.7 MB'
  });

  const [currentTime, setCurrentTime] = useState(new Date());

  // Update time every second
  useEffect(() => {
    const timeInterval = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timeInterval);
  }, []);

  return (
    <div style={{
      height: '28px',
      background: 'var(--bg-secondary)',
      borderTop: '1px solid var(--border-primary)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 16px',
      fontSize: '11px',
      color: 'var(--text-muted)',
      flexShrink: 0
    }}>
      {/* Left Section - Project Info */}
      <div style={{display: 'flex', alignItems: 'center', gap: '16px'}}>
        <div style={{display: 'flex', alignItems: 'center', gap: '6px'}}>
          <div style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: '#10B981'
          }}></div>
          <span style={{fontWeight: 500}}>{projectInfo.name}</span>
        </div>
        
        <div style={{display: 'flex', alignItems: 'center', gap: '12px'}}>
          <span>⏱️ {projectInfo.duration}</span>
          <span>💾 {projectInfo.size}</span>
        </div>
      </div>

      {/* Right Section - Time */}
      <div style={{display: 'flex', alignItems: 'center', gap: '4px'}}>
        <Clock style={{width: '12px', height: '12px'}} />
        {currentTime.toLocaleTimeString()}
      </div>
    </div>
  );
};

// Enhanced Professional Toolbar with more features
const EnhancedProfessionalToolbar = ({ onBackToDashboard }: { onBackToDashboard?: () => void }) => {
  const [undoStack, setUndoStack] = useState(0);
  const [redoStack, setRedoStack] = useState(0);
  const [isRecording, setIsRecording] = useState(false);
  const [autosaveStatus, setAutosaveStatus] = useState<'saved' | 'saving' | 'error'>('saved');
  const [projectName, setProjectName] = useState('Untitled Project');
  const [isEditingProjectName, setIsEditingProjectName] = useState(false);

  const handleProjectNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setProjectName(e.target.value);
  };

  const handleProjectNameSubmit = () => {
    setIsEditingProjectName(false);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleProjectNameSubmit();
    }
    if (e.key === 'Escape') {
      setIsEditingProjectName(false);
    }
  };

  return (
    <div style={{
      background: 'var(--gradient-surface)',
      borderBottom: '1px solid var(--border-primary)',
      padding: '8px 16px',
      display: 'flex',
      alignItems: 'center',
      gap: '16px',
      flexShrink: 0,
      height: '48px'
    }}>
      {/* Back to Dashboard */}
      {onBackToDashboard && (
        <button
          className="tooltip hover-lift micro-bounce"
          data-tooltip="Back to Dashboard"
          onClick={onBackToDashboard}
          style={{
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-primary)',
            borderRadius: 'var(--radius-md)',
            padding: '6px 8px',
            color: 'var(--text-primary)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '13px',
            fontWeight: 500
          }}
        >
          <ArrowLeft style={{width: '14px', height: '14px'}} />
          Back
        </button>
      )}

      {/* File Operations */}
      <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
        <button
          className="tooltip hover-lift micro-bounce"
          data-tooltip="New Project (Ctrl+N)"
          style={{
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-primary)',
            borderRadius: 'var(--radius-md)',
            padding: '6px 8px',
            color: 'var(--text-primary)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '13px',
            fontWeight: 500
          }}
        >
          <FileText style={{width: '14px', height: '14px'}} />
          New
        </button>

        <button
          className="tooltip hover-lift micro-bounce"
          data-tooltip="Save Project (Ctrl+S)"
          style={{
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-primary)',
            borderRadius: 'var(--radius-md)',
            padding: '6px 8px',
            color: 'var(--text-primary)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '13px',
            fontWeight: 500
          }}
        >
          <Save style={{width: '14px', height: '14px'}} />
          Save
        </button>
          </div>

      {/* Divider */}
      <div style={{width: '1px', height: '24px', background: 'var(--border-primary)'}}></div>

      {/* Edit Tools */}
      <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
        <button
          className="tooltip hover-lift micro-bounce"
          data-tooltip="Undo (Ctrl+Z)"
          style={{
            background: undoStack > 0 ? 'var(--bg-tertiary)' : 'var(--bg-secondary)',
            border: '1px solid var(--border-primary)',
            borderRadius: 'var(--radius-md)',
            padding: '6px 8px',
            color: undoStack > 0 ? 'var(--text-primary)' : 'var(--text-disabled)',
            cursor: undoStack > 0 ? 'pointer' : 'not-allowed',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '13px',
            fontWeight: 500
          }}
          disabled={undoStack === 0}
        >
          <Undo style={{width: '14px', height: '14px'}} />
          Undo
        </button>

        <button
          className="tooltip hover-lift micro-bounce"
          data-tooltip="Redo (Ctrl+Y)"
          style={{
            background: redoStack > 0 ? 'var(--bg-tertiary)' : 'var(--bg-secondary)',
            border: '1px solid var(--border-primary)',
            borderRadius: 'var(--radius-md)',
            padding: '6px 8px',
            color: redoStack > 0 ? 'var(--text-primary)' : 'var(--text-disabled)',
            cursor: redoStack > 0 ? 'pointer' : 'not-allowed',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '13px',
            fontWeight: 500
          }}
          disabled={redoStack === 0}
        >
          <Redo style={{width: '14px', height: '14px'}} />
          Redo
        </button>
            </div>

      {/* Center - Project Name & Recording Status */}
      <div style={{
        position: 'absolute',
        left: '47%',
        transform: 'translateX(-50%)',
        display: 'flex',
        alignItems: 'center',
        gap: '16px'
      }}>
        {/* Editable Project Name */}
        <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
          <span style={{color: 'var(--accent-blue)', fontWeight: 600, fontSize: '14px'}}>Sclips</span>
          <span style={{color: 'var(--text-muted)'}}>•</span>
          {isEditingProjectName ? (
              <input
                type="text"
              value={projectName}
              onChange={handleProjectNameChange}
              onBlur={handleProjectNameSubmit}
              onKeyPress={handleKeyPress}
              autoFocus
              style={{
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--accent-blue)',
                borderRadius: '4px',
                padding: '4px 8px',
                color: 'var(--text-primary)',
                fontSize: '13px',
                fontWeight: 500,
                outline: 'none',
                minWidth: '120px'
              }}
            />
          ) : (
            <span 
              onClick={() => setIsEditingProjectName(true)}
              style={{
                cursor: 'pointer',
                padding: '4px 8px',
                borderRadius: '4px',
                transition: 'background var(--transition-fast)',
                fontSize: '13px',
                fontWeight: 500,
                color: 'var(--text-primary)'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(59, 130, 246, 0.1)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent';
              }}
            >
              {projectName}
            </span>
          )}
        </div>

        {/* Recording Status */}
        {isRecording && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: 'var(--radius-lg)',
            padding: '6px 12px',
            color: '#EF4444',
            fontSize: '12px',
            fontWeight: 600
          }}>
            <div style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: '#EF4444',
              animation: 'pulse 1s ease-in-out infinite'
            }}></div>
            Recording Timeline Actions
          </div>
        )}
      </div>

      {/* Right Side - Status & Export */}
      <div style={{marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '12px'}}>
        {/* Autosave Status */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontSize: '12px',
          color: autosaveStatus === 'saved' ? '#10B981' : 
                 autosaveStatus === 'saving' ? '#F59E0B' : '#EF4444'
        }}>
          {autosaveStatus === 'saved' && <Check style={{width: '12px', height: '12px'}} />}
          {autosaveStatus === 'saving' && <RefreshCw style={{width: '12px', height: '12px', animation: 'spin 1s linear infinite'}} />}
          {autosaveStatus === 'error' && <AlertCircle style={{width: '12px', height: '12px'}} />}
          {autosaveStatus === 'saved' ? 'Saved' : 
           autosaveStatus === 'saving' ? 'Saving...' : 'Error'}
        </div>

        {/* Quick Export */}
        <button
          className="tooltip hover-glow button-ripple"
          data-tooltip="Quick Export (Ctrl+E)"
          style={{
            background: 'var(--gradient-accent)',
            border: 'none',
            borderRadius: 'var(--radius-md)',
            padding: '8px 16px',
            color: 'white',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '13px',
            fontWeight: 600,
            boxShadow: 'var(--shadow-moderate)'
          }}
        >
          <Download style={{width: '14px', height: '14px'}} />
          Export
              </button>

        {/* Settings */}
        <button
          className="tooltip micro-rotate"
          data-tooltip="Project Settings"
          style={{
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-primary)',
            borderRadius: 'var(--radius-md)',
            padding: '6px',
            color: 'var(--text-primary)',
            cursor: 'pointer'
          }}
        >
          <Settings style={{width: '16px', height: '16px'}} />
        </button>
          </div>
        </div>
  );
};

// Enhanced Floating Bubbles with Natural Movement and Collisions
const EnhancedFloatingBubbles = () => {
  const [bubbles, setBubbles] = useState(() => 
    Array.from({ length: 8 }, (_, i) => ({
      id: i,
      x: Math.random() * window.innerWidth,
      y: Math.random() * window.innerHeight,
      vx: (Math.random() - 0.5) * 0.5,
      vy: (Math.random() - 0.5) * 0.5,
      size: 250 + Math.random() * 80, // 60-140px
      opacity: 0.5 + Math.random() * 0.3, // 0.2-0.5
      hue: Math.random() * 60 + 200, // Blue to purple range
    }))
  );

  useEffect(() => {
    const animateBubbles = () => {
      setBubbles(prevBubbles => 
        prevBubbles.map(bubble => {
          let newX = bubble.x + bubble.vx;
          let newY = bubble.y + bubble.vy;
          let newVx = bubble.vx;
          let newVy = bubble.vy;

          // Bounce off walls
          if (newX <= bubble.size/2 || newX >= window.innerWidth - bubble.size/2) {
            newVx = -newVx;
            newX = Math.max(bubble.size/2, Math.min(window.innerWidth - bubble.size/2, newX));
          }
          if (newY <= bubble.size/2 || newY >= window.innerHeight - bubble.size/2) {
            newVy = -newVy;
            newY = Math.max(bubble.size/2, Math.min(window.innerHeight - bubble.size/2, newY));
          }

          // Check collisions with other bubbles
          prevBubbles.forEach(otherBubble => {
            if (otherBubble.id !== bubble.id) {
              const dx = newX - otherBubble.x;
              const dy = newY - otherBubble.y;
              const distance = Math.sqrt(dx * dx + dy * dy);
              const minDistance = (bubble.size + otherBubble.size) / 2;

              if (distance < minDistance && distance > 0) {
                // Collision detected - bounce off each other
                const angle = Math.atan2(dy, dx);
                const bounce = 0.3;
                newVx += Math.cos(angle) * bounce;
                newVy += Math.sin(angle) * bounce;
                
                // Separate bubbles
                const separation = (minDistance - distance) / 2;
                newX += Math.cos(angle) * separation;
                newY += Math.sin(angle) * separation;
              }
            }
          });

          // Add some randomness
          newVx += (Math.random() - 0.5) * 0.02;
          newVy += (Math.random() - 0.5) * 0.02;

          // Limit velocity
          const maxVelocity = 1;
          const velocity = Math.sqrt(newVx * newVx + newVy * newVy);
          if (velocity > maxVelocity) {
            newVx = (newVx / velocity) * maxVelocity;
            newVy = (newVy / velocity) * maxVelocity;
          }

          return {
            ...bubble,
            x: newX,
            y: newY,
            vx: newVx,
            vy: newVy,
          };
        })
      );
    };

    const interval = setInterval(animateBubbles, 16); // ~60fps
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="enhanced-floating-bubbles">
      {bubbles.map(bubble => (
        <div
          key={bubble.id}
          className="natural-bubble"
          style={{
            left: `${bubble.x - bubble.size/2}px`,
            top: `${bubble.y - bubble.size/2}px`,
            width: `${bubble.size}px`,
            height: `${bubble.size}px`,
            opacity: bubble.opacity,
            background: `radial-gradient(circle at 30% 30%, 
              hsla(${bubble.hue}, 70%, 70%, 0.6), 
              hsla(${bubble.hue}, 50%, 50%, 0.3), 
              hsla(${bubble.hue}, 30%, 30%, 0.1))`,
            boxShadow: `
              inset ${bubble.size * 0.1}px ${bubble.size * 0.1}px ${bubble.size * 0.2}px rgba(255, 255, 255, 0.3),
              0 0 ${bubble.size * 0.3}px hsla(${bubble.hue}, 60%, 60%, 0.4)
            `,
          }}
        />
      ))}
      </div>
  );
};

// Floating Bubbles Background Component  
const FloatingBubbles = () => <EnhancedFloatingBubbles />;

// Main App Component with dashboard system
const App = () => {
  const [currentView, setCurrentView] = useState<'dashboard' | 'editor'>('dashboard');
  const [currentProject, setCurrentProject] = useState<any>(null);

  const handleOpenProject = (project: any) => {
    setCurrentProject(project);
    setCurrentView('editor');
  };

  const handleCreateProject = () => {
    setCurrentView('editor');
  };

  const handleBackToDashboard = () => {
    setCurrentProject(null);
    setCurrentView('dashboard');
  };

  if (currentView === 'dashboard') {
    return (
      <SelectedTagsProvider>
        <Dashboard 
          onOpenProject={handleOpenProject}
          onCreateProject={handleCreateProject}
        />
      </SelectedTagsProvider>
    );
  }

  return (
    <SelectedTagsProvider>
      <div className="sclips-app-root">
        <FloatingBubbles />
        <EnhancedProfessionalToolbar onBackToDashboard={handleBackToDashboard} />
        <div className="main-content">
          <div className="main-editor">
            <MainEditorGrid currentProject={currentProject} />
        </div>
          <div className="ai-panel">
            <AIChatPanel currentProject={currentProject} />
          </div>
        </div>
        <StatusBar />
      </div>
    </SelectedTagsProvider>
  );
};

function ConnectionStatusBar() {
  const { connectionStatus, error } = useRealtimeStore();
  return (
    <div style={{
      position: "fixed", bottom: 0, left: 0, right: 0,
      background: "#222", color: "#fff", fontSize: 12, padding: 4, zIndex: 1000
    }}>
      Status: {connectionStatus}
      {error && <span style={{ color: "red", marginLeft: 16 }}>Error: {error}</span>}
    </div>
  );
}

export default App;
