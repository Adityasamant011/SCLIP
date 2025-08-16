import React from 'react';
import { Message } from '../hooks/useRealtimeStore';
import { useStreamingMessage } from '../hooks/useStreamingMessage';

interface StreamingMessageProps {
  message: Message;
  onComplete?: () => void;
  streamingSpeed?: number; // milliseconds per character
}

const StreamingMessage: React.FC<StreamingMessageProps> = ({ 
  message, 
  onComplete, 
  streamingSpeed = 25 
}) => {
  const {
    displayedText,
    isStreaming,
    showCursor,
    isComplete,
    messageRef,
    stopStreaming,
    startStreaming
  } = useStreamingMessage({
    message,
    streamingSpeed,
    onComplete
  });

  // For thinking messages, don't use streaming - show immediately
  if (message.type === 'thinking') {
    return (
      <div className="chat-message thinking">
        <div className="chat-bubble thinking-bubble">
          <div className="thinking-icon">🤔</div>
          <div className="thinking-content">
            <div className="thinking-text">Thinking...</div>
            <div className="thinking-dots">
              <span className="dot"></span>
              <span className="dot"></span>
              <span className="dot"></span>
            </div>
          </div>
        </div>
      </div>
    );
  }



  const renderMessageContent = () => {
    switch (message.type) {
      case 'ai_message':
        return (
          <div 
            className="chat-bubble ai-bubble" 
            ref={messageRef}
            onClick={isStreaming ? stopStreaming : undefined}
            style={{ cursor: isStreaming ? 'pointer' : 'default' }}
            title={isStreaming ? 'Click to skip animation' : undefined}
          >
            <div className="ai-avatar">🤖</div>
            <div className="ai-content">
              {displayedText}
              {showCursor && <span className="typing-cursor">|</span>}
            </div>
          </div>
        );
        
      case 'agent_thinking':
        return (
          <div className="chat-bubble agent-thinking-bubble">
            <div className="agent-avatar">🤔</div>
            <div className="agent-content">
              <div className="agent-thinking-text">{displayedText}</div>
              {message.iteration && (
                <div className="agent-iteration">Iteration {message.iteration}</div>
              )}
              <div className="agent-thinking-dots">
                <span className="dot"></span>
                <span className="dot"></span>
                <span className="dot"></span>
              </div>
            </div>
          </div>
        );
        
      case 'agent_executing':
        return (
          <div className="chat-bubble agent-executing-bubble">
            <div className="agent-avatar">⚡</div>
            <div className="agent-content">
              <div className="agent-executing-text">{displayedText}</div>
              {message.iteration && (
                <div className="agent-iteration">Iteration {message.iteration}</div>
              )}
              {message.actions && message.actions.length > 0 && (
                <div className="agent-actions">
                  <div className="actions-title">Executing:</div>
                  {message.actions.map((action: string, i: number) => (
                    <div key={i} className="action-item">• {action}</div>
                  ))}
                </div>
              )}
            </div>
          </div>
        );
        
      case 'agent_streaming_start':
        return (
          <div className="chat-bubble agent-streaming-bubble">
            <div className="agent-avatar">🤔</div>
            <div className="agent-content">
              <div className="agent-streaming-text">{displayedText}</div>
              <div className="agent-streaming-dots">
                <span className="dot"></span>
                <span className="dot"></span>
                <span className="dot"></span>
              </div>
            </div>
          </div>
        );
        
      case 'agent_streaming_complete':
        return (
          <div className="chat-bubble agent-complete-bubble">
            <div className="agent-avatar">✅</div>
            <div className="agent-content">
              <div className="agent-complete-text">{displayedText}</div>
            </div>
          </div>
        );
        
      case 'user_message':
        return (
          <div className="chat-bubble user-bubble">
            <div className="user-content">{displayedText}</div>
            <div className="user-avatar">👤</div>
          </div>
        );
        
      case 'informational':
        return (
          <div className="chat-bubble info-bubble">
            <div className="info-icon">ℹ️</div>
            <div className="info-content">
              <div className="info-title">{displayedText}</div>
              {message.capabilities && (
                <div className="capabilities-list">
                  {message.capabilities.map((cap: string, i: number) => (
                    <div key={i} className="capability-item">• {cap}</div>
                  ))}
                </div>
              )}
              {message.suggestions && (
                <div className="suggestions-list">
                  <div className="suggestions-title">Try these:</div>
                  {message.suggestions.map((suggestion: string, i: number) => (
                    <div key={i} className="suggestion-item">
                      💡 {suggestion}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        );
        
      case 'tool_call':
        return (
          <div className="chat-bubble tool-bubble">
            <div className="tool-icon">⚙️</div>
            <div className="tool-content">
              <div className="tool-header">
                <div className="tool-name">{message.tool}</div>
                <div className="tool-status">Executing...</div>
              </div>
              <div className="tool-description">{message.description}</div>
              {message.args && (
                <div className="tool-args">
                  <div className="args-label">Parameters:</div>
                  <pre className="args-json">{JSON.stringify(message.args, null, 2)}</pre>
                </div>
              )}
              <div className="tool-reasoning">
                <div className="reasoning-icon">🤔</div>
                <div className="reasoning-text">Agent reasoning: {message.description}</div>
              </div>
            </div>
          </div>
        );
        
      case 'tool_result':
        return (
          <div className="chat-bubble result-bubble">
            <div className="result-icon">{message.success ? "✅" : "❌"}</div>
            <div className="result-content">
              <div className="result-header">
                <div className="result-tool">{message.tool}</div>
                <div className="result-status">{message.success ? "Success" : "Failed"}</div>
              </div>
              {message.success && message.result && (
                <div className="result-details">
                  <div className="result-summary">
                    {message.tool === 'script_writer' && 'Script generated successfully'}
                    {message.tool === 'broll_finder' && `${message.result.downloaded_files?.length || 0} media files found`}
                    {message.tool === 'voiceover_generator' && 'Voiceover created successfully'}
                    {message.tool === 'video_processor' && 'Video processing completed'}
                  </div>
                  {message.result && typeof message.result === 'object' && (
                    <details className="result-raw">
                      <summary>View Details</summary>
                      <pre>{JSON.stringify(message.result, null, 2)}</pre>
                    </details>
                  )}
                </div>
              )}
              {!message.success && message.error && (
                <div className="result-error">
                  <div className="error-message">{message.error}</div>
                </div>
              )}
            </div>
          </div>
        );
        
      case 'progress':
        return (
          <div className="chat-bubble progress-bubble">
            <div className="progress-icon">🔄</div>
            <div className="progress-content">
              <div className="progress-step">{message.step}</div>
              <div className="progress-bar">
                <div className="progress-fill" style={{width: `${message.percent}%`}}></div>
              </div>
              <div className="progress-status">{message.status}</div>
            </div>
          </div>
        );
        
      case 'error':
        return (
          <div className="chat-bubble error-bubble">
            <div className="error-icon">❌</div>
            <div className="error-content">{message.message || message.detail}</div>
          </div>
        );
        
      default:
        return (
          <div className="chat-bubble default-bubble">
            <div className="default-content">{displayedText}</div>
          </div>
        );
    }
  };

  return (
    <div className={`chat-message ${message.type}`}>
      {renderMessageContent()}
    </div>
  );
};

export default StreamingMessage; 