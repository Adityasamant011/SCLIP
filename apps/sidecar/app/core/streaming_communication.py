"""
Streaming Communication System - Cursor-like Real-time Updates
Provides rich streaming communication with progress updates, contextual information, and interactive suggestions
"""

import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional, Callable, AsyncGenerator
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import logging

from ..utils.logger import get_logger

logger = get_logger(__name__)

class MessageType(Enum):
    """Types of streaming messages"""
    THINKING = "thinking"
    PROGRESS = "progress"
    ACTION_START = "action_start"
    ACTION_PROGRESS = "action_progress"
    ACTION_COMPLETE = "action_complete"
    WORKFLOW_UPDATE = "workflow_update"
    SUGGESTION = "suggestion"
    CONTEXT_UPDATE = "context_update"
    ERROR = "error"
    SUCCESS = "success"

@dataclass
class StreamingMessage:
    """Represents a streaming message"""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.THINKING
    content: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: str = ""
    progress: Optional[float] = None
    personality: str = "enthusiastic"

class ProgressTracker:
    """Tracks progress for long-running operations"""
    
    def __init__(self, operation_id: str, total_steps: int = 1):
        self.operation_id = operation_id
        self.total_steps = total_steps
        self.current_step = 0
        self.step_details: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
        self.estimated_duration: Optional[int] = None
    
    def update_progress(self, step: int, description: str, details: Dict[str, Any] = None) -> float:
        """Update progress and return percentage"""
        self.current_step = step
        step_info = {
            "step": step,
            "description": description,
            "timestamp": datetime.now(),
            "details": details or {}
        }
        self.step_details.append(step_info)
        
        progress = (step / self.total_steps) * 100
        return progress
    
    def get_progress_info(self) -> Dict[str, Any]:
        """Get current progress information"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "operation_id": self.operation_id,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "progress_percentage": (self.current_step / self.total_steps) * 100,
            "elapsed_seconds": elapsed,
            "estimated_remaining": self._estimate_remaining(elapsed),
            "step_details": self.step_details
        }
    
    def _estimate_remaining(self, elapsed: float) -> Optional[float]:
        """Estimate remaining time based on current progress"""
        if self.current_step == 0:
            return None
        
        if self.estimated_duration:
            return max(0, self.estimated_duration - elapsed)
        
        # Estimate based on current pace
        if elapsed > 0:
            pace = elapsed / self.current_step
            remaining_steps = self.total_steps - self.current_step
            return pace * remaining_steps
        
        return None

class StreamingCommunicationManager:
    """Manages rich streaming communication for Cursor-like experience"""
    
    def __init__(self, websocket_manager):
        self.websocket_manager = websocket_manager
        self.progress_trackers: Dict[str, ProgressTracker] = {}
        self.active_streams: Dict[str, asyncio.Task] = {}
        self.message_handlers: Dict[MessageType, List[Callable]] = {}
    
    async def stream_workflow_progress(self, session_id: str, workflow_plan: Dict[str, Any]) -> None:
        """Stream workflow progress with rich updates"""
        
        operation_id = f"workflow_{session_id}_{uuid.uuid4().hex[:8]}"
        total_steps = len(workflow_plan.get("steps", []))
        
        # Create progress tracker
        tracker = ProgressTracker(operation_id, total_steps)
        self.progress_trackers[operation_id] = tracker
        
        # Send initial workflow overview
        await self._send_workflow_overview(session_id, workflow_plan)
        
        # Stream progress updates
        for i, step in enumerate(workflow_plan.get("steps", []), 1):
            await self._stream_step_progress(session_id, step, tracker, i)
    
    async def _send_workflow_overview(self, session_id: str, workflow_plan: Dict[str, Any]) -> None:
        """Send workflow overview message"""
        
        steps = workflow_plan.get("steps", [])
        estimated_duration = workflow_plan.get("estimated_duration", 0)
        
        overview_message = StreamingMessage(
            type=MessageType.WORKFLOW_UPDATE,
            content=f"🎬 Planning your video workflow: {len(steps)} steps, ~{estimated_duration//60} minutes",
            data={
                "workflow_type": workflow_plan.get("type", "basic"),
                "total_steps": len(steps),
                "estimated_duration": estimated_duration,
                "phases": workflow_plan.get("phases", [])
            },
            session_id=session_id,
            personality="enthusiastic"
        )
        
        await self._send_message(session_id, overview_message)
    
    async def _stream_step_progress(self, session_id: str, step: Dict[str, Any], tracker: ProgressTracker, step_number: int) -> None:
        """Stream progress for a single step"""
        
        step_name = step.get("name", "Unknown step")
        step_description = step.get("description", "")
        
        # Send step start
        start_message = StreamingMessage(
            type=MessageType.ACTION_START,
            content=f"🚀 Starting: {step_description}",
            data={
                "step_number": step_number,
                "step_name": step_name,
                "step_description": step_description,
                "action_type": step.get("action_type", "")
            },
            session_id=session_id,
            personality="enthusiastic"
        )
        
        await self._send_message(session_id, start_message)
        
        # Update progress
        progress = tracker.update_progress(step_number, step_description)
        
        # Send progress update
        progress_message = StreamingMessage(
            type=MessageType.PROGRESS,
            content=f"📊 Progress: {progress:.1f}% - {step_description}",
            data=tracker.get_progress_info(),
            session_id=session_id,
            progress=progress,
            personality="informative"
        )
        
        await self._send_message(session_id, progress_message)
        
        # Simulate step execution time
        await asyncio.sleep(2)
        
        # Send step completion
        complete_message = StreamingMessage(
            type=MessageType.ACTION_COMPLETE,
            content=f"✅ Completed: {step_description}",
            data={
                "step_number": step_number,
                "step_name": step_name,
                "result": "success"
            },
            session_id=session_id,
            personality="enthusiastic"
        )
        
        await self._send_message(session_id, complete_message)
    
    async def stream_thinking_process(self, session_id: str, user_message: str) -> None:
        """Stream thinking process with personality - Cursor-like experience"""
        
        thinking_steps = [
            ("🤔 Analyzing your request with excitement...", 0.2),
            ("🧠 Understanding your creative vision...", 0.4),
            ("💡 Planning the perfect approach...", 0.6),
            ("🎬 Preparing to create something amazing...", 0.8),
            ("✨ Ready to bring your idea to life!", 1.0)
        ]
        
        for message, progress in thinking_steps:
            thinking_message = StreamingMessage(
                type=MessageType.THINKING,
                content=message,
                data={"progress": progress, "user_message": user_message},
                session_id=session_id,
                progress=progress * 100,
                personality="enthusiastic"
            )
            
            await self._send_message(session_id, thinking_message)
            
            # Add natural delay for better UX - like Cursor
            await asyncio.sleep(2.5)
    
    async def stream_action_execution(self, session_id: str, action_type: str, action_description: str) -> None:
        """Stream detailed progress for action execution - Cursor-like experience"""
        
        # Action-specific progress messages with realistic timing
        action_progress = {
            "create_script": [
                ("📝 Crafting your story...", 0.25),
                ("✍️ Writing compelling content...", 0.5),
                ("🎯 Structuring the narrative...", 0.75),
                ("✨ Finalizing your script!", 1.0)
            ],
            "find_media": [
                ("🔍 Searching for perfect visuals...", 0.25),
                ("📸 Finding high-quality content...", 0.5),
                ("🎨 Curating the best options...", 0.75),
                ("✅ Media collection complete!", 1.0)
            ],
            "generate_voiceover": [
                ("🎤 Preparing voice synthesis...", 0.25),
                ("🗣️ Generating professional narration...", 0.5),
                ("🎵 Adding natural intonation...", 0.75),
                ("🎧 Voiceover ready!", 1.0)
            ],
            "process_video": [
                ("🎬 Assembling your video...", 0.25),
                ("🎨 Adding visual effects...", 0.5),
                ("🎵 Syncing audio and visuals...", 0.75),
                ("🎉 Video processing complete!", 1.0)
            ]
        }
        
        # Get progress steps for this action type
        progress_steps = action_progress.get(action_type, [
            ("⚡ Processing your request...", 0.5),
            ("✅ Action completed!", 1.0)
        ])
        
        # Stream progress updates with realistic timing
        for message, progress in progress_steps:
            progress_message = StreamingMessage(
                type=MessageType.ACTION_PROGRESS,
                content=message,
                data={
                    "action_type": action_type,
                    "action_description": action_description,
                    "progress": progress
                },
                session_id=session_id,
                progress=progress * 100,
                personality="enthusiastic"
            )
            
            await self._send_message(session_id, progress_message)
            
            # Add realistic delay - like Cursor's natural progression
            await asyncio.sleep(4)
    
    async def send_contextual_suggestion(self, session_id: str, context: Dict[str, Any]) -> None:
        """Send intelligent, context-aware suggestions"""
        
        suggestions = self._generate_contextual_suggestions(context)
        
        if suggestions:
            # Create suggestion message
            suggestion_text = " | ".join([s["text"] for s in suggestions[:3]])
            
            suggestion_message = StreamingMessage(
                type=MessageType.SUGGESTION,
                content=f"💡 **Smart Suggestions:** {suggestion_text}",
                data={
                    "suggestions": suggestions,
                    "context": context
                },
                session_id=session_id,
                personality="helpful"
            )
            
            await self._send_message(session_id, suggestion_message)
    
    def _generate_contextual_suggestions(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate intelligent suggestions based on context"""
        
        suggestions = []
        completed_actions = context.get("completed_actions", [])
        current_project = context.get("current_project", {})
        
        # Check what's been completed and suggest next steps
        if "create_script" in completed_actions and "find_media" not in completed_actions:
            suggestions.append({
                "text": "Find stunning visuals to match your script",
                "action": "find_media",
                "priority": "high"
            })
        
        if "create_script" in completed_actions and "find_media" in completed_actions and "generate_voiceover" not in completed_actions:
            suggestions.append({
                "text": "Add professional voiceover narration",
                "action": "generate_voiceover",
                "priority": "medium"
            })
        
        if "find_media" in completed_actions and "process_video" not in completed_actions:
            suggestions.append({
                "text": "Assemble your final video",
                "action": "process_video",
                "priority": "high"
            })
        
        # Check project state for additional suggestions
        if current_project.get("scripts") and not current_project.get("media"):
            suggestions.append({
                "text": "Your script is ready! Want to find some amazing visuals?",
                "action": "find_media",
                "priority": "high"
            })
        
        if current_project.get("media") and not current_project.get("voiceovers"):
            suggestions.append({
                "text": "Great visuals! Should we add a professional voiceover?",
                "action": "generate_voiceover",
                "priority": "medium"
            })
        
        # Add general suggestions if no specific ones
        if not suggestions:
            suggestions.append({
                "text": "Ready to create something amazing? Let's start with a script!",
                "action": "create_script",
                "priority": "medium"
            })
        
        return suggestions
    
    async def send_context_update(self, session_id: str, context_type: str, data: Dict[str, Any]) -> None:
        """Send context update to keep frontend informed"""
        
        context_message = StreamingMessage(
            type=MessageType.CONTEXT_UPDATE,
            content=f"📊 Updated {context_type} context",
            data={
                "context_type": context_type,
                "data": data,
                "timestamp": datetime.now().isoformat()
            },
            session_id=session_id,
            personality="informative"
        )
        
        await self._send_message(session_id, context_message)
    
    async def _send_message(self, session_id: str, message: StreamingMessage) -> None:
        """Send a streaming message to the frontend"""
        
        # Convert message to dict for JSON serialization
        message_dict = {
            "message_id": message.message_id,
            "type": message.type.value,
            "content": message.content,
            "data": message.data,
            "timestamp": message.timestamp.isoformat(),
            "session_id": message.session_id,
            "personality": message.personality
        }
        
        if message.progress is not None:
            message_dict["progress"] = message.progress
        
        # Send via websocket manager
        try:
            await self.websocket_manager.send_message(session_id, message_dict)
            logger.debug(f"Sent streaming message: {message.type.value} to session {session_id}")
        except Exception as e:
            logger.error(f"Error sending streaming message: {e}")
    
    async def create_interactive_stream(self, session_id: str, stream_type: str) -> AsyncGenerator[StreamingMessage, None]:
        """Create an interactive streaming session"""
        
        stream_id = f"{stream_type}_{session_id}_{uuid.uuid4().hex[:8]}"
        
        try:
            # Send stream start
            start_message = StreamingMessage(
                type=MessageType.PROGRESS,
                content=f"🎬 Starting {stream_type} stream...",
                data={"stream_id": stream_id, "stream_type": stream_type},
                session_id=session_id
            )
            
            yield start_message
            
            # This is a placeholder for actual interactive streaming
            # In a real implementation, this would handle user interactions
            
        except Exception as e:
            error_message = StreamingMessage(
                type=MessageType.ERROR,
                content=f"Error in {stream_type} stream: {str(e)}",
                data={"stream_id": stream_id, "error": str(e)},
                session_id=session_id
            )
            yield error_message
    
    def register_message_handler(self, message_type: MessageType, handler: Callable) -> None:
        """Register a message handler for a specific message type"""
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        
        self.message_handlers[message_type].append(handler)
    
    async def handle_incoming_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """Handle incoming messages from frontend"""
        
        message_type = message.get("type")
        if not message_type:
            return
        
        try:
            # Convert string to enum
            msg_type = MessageType(message_type)
            
            # Call registered handlers
            if msg_type in self.message_handlers:
                for handler in self.message_handlers[msg_type]:
                    await handler(session_id, message)
            
        except ValueError:
            logger.warning(f"Unknown message type: {message_type}")
        except Exception as e:
            logger.error(f"Error handling incoming message: {e}")
    
    def get_progress_info(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get progress information for an operation"""
        tracker = self.progress_trackers.get(operation_id)
        if tracker:
            return tracker.get_progress_info()
        return None
    
    def cleanup_operation(self, operation_id: str) -> None:
        """Clean up operation resources"""
        if operation_id in self.progress_trackers:
            del self.progress_trackers[operation_id]
        
        if operation_id in self.active_streams:
            self.active_streams[operation_id].cancel()
            del self.active_streams[operation_id] 