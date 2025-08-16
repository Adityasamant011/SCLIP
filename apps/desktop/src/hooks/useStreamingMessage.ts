import { useState, useEffect, useRef, useCallback } from 'react';
import { Message } from './useRealtimeStore';

interface UseStreamingMessageOptions {
  message: Message;
  streamingSpeed?: number;
  onComplete?: () => void;
}

export const useStreamingMessage = ({ 
  message, 
  streamingSpeed = 15, 
  onComplete 
}: UseStreamingMessageOptions) => {
  const [displayedText, setDisplayedText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [showCursor, setShowCursor] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const fullText = message.content || message.message || message.detail || '';
  const messageRef = useRef<HTMLDivElement>(null);
  const streamIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const startStreaming = useCallback(() => {
    if (message.type !== 'ai_message' || !fullText || isStreaming) return;

    setIsStreaming(true);
    setDisplayedText('');
    setShowCursor(true);
    setIsComplete(false);

    let currentIndex = 0;
    streamIntervalRef.current = setInterval(() => {
      if (currentIndex < fullText.length) {
        setDisplayedText(prev => prev + fullText[currentIndex]);
        currentIndex++;
        
        // Auto-scroll to bottom as text streams
        if (messageRef.current) {
          messageRef.current.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'end' 
          });
        }
      } else {
        if (streamIntervalRef.current) {
          clearInterval(streamIntervalRef.current);
          streamIntervalRef.current = null;
        }
        setIsStreaming(false);
        setShowCursor(false);
        setIsComplete(true);
        onComplete?.();
      }
    }, streamingSpeed);
  }, [message.type, fullText, isStreaming, streamingSpeed, onComplete]);

  const stopStreaming = useCallback(() => {
    if (streamIntervalRef.current) {
      clearInterval(streamIntervalRef.current);
      streamIntervalRef.current = null;
    }
    setIsStreaming(false);
    setShowCursor(false);
    setDisplayedText(fullText);
    setIsComplete(true);
  }, [fullText]);

  // Handle cursor blinking
  useEffect(() => {
    if (!showCursor) return;
    
    const cursorInterval = setInterval(() => {
      setShowCursor(prev => !prev);
    }, 500);
    
    return () => clearInterval(cursorInterval);
  }, [showCursor]);

  // Handle message updates
  useEffect(() => {
    if (message.type === 'ai_message' && fullText) {
      if (message.is_partial) {
        // Handle partial messages from backend - update existing text
        setDisplayedText(fullText);
        setShowCursor(true);
        setIsStreaming(true);
        setIsComplete(false);
        
        if (messageRef.current) {
          messageRef.current.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'end' 
          });
        }
      } else if (message.is_complete) {
        // Final complete message
        setDisplayedText(fullText);
        setIsStreaming(false);
        setShowCursor(false);
        setIsComplete(true);
        onComplete?.();
      } else if (!isStreaming && !isComplete) {
        // Start character-by-character streaming
        startStreaming();
      }
    } else if (message.type !== 'ai_message') {
      // Non-AI messages show immediately
      setDisplayedText(fullText);
      setIsStreaming(false);
      setShowCursor(false);
      setIsComplete(true);
    }
  }, [message, fullText, isStreaming, isComplete, startStreaming, onComplete]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (streamIntervalRef.current) {
        clearInterval(streamIntervalRef.current);
      }
    };
  }, []);

  return {
    displayedText,
    isStreaming,
    showCursor,
    isComplete,
    messageRef,
    stopStreaming,
    startStreaming
  };
}; 