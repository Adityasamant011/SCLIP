"""
Message Handler for SclipBrain Orchestrator
Handles real-time communication with frontend and implements dual-response pattern
"""
import json
import asyncio
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from datetime import datetime
from pydantic import BaseModel

from apps.sidecar.app.utils.logger import get_logger

logger = get_logger(__name__)

class MessageType(Enum):
    """Types of messages sent between orchestrator and frontend"""
    AI_MESSAGE = "ai_message"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    PROGRESS = "progress"
    USER_INPUT_REQUEST = "user_input_request"
    ERROR = "error"
    PROCESS_PAUSED = "process_paused"
    PROCESS_RESUMED = "process_resumed"
    WORKFLOW_COMPLETE = "workflow_complete"

class Message(BaseModel):
    """Base message model for all communication"""
    type: MessageType
    timestamp: datetime
    session_id: str
    data: Dict[str, Any]

class AIMessage(Message):
    """AI agent's user-facing message"""
    type: MessageType = MessageType.AI_MESSAGE
    content: str
    step_id: Optional[str] = None

class ToolCallMessage(Message):
    """Message indicating a tool is being called"""
    type: MessageType = MessageType.TOOL_CALL
    tool: str
    args: Dict[str, Any]
    step_id: str
    description: str

class ToolResultMessage(Message):
    """Message containing tool execution result"""
    type: MessageType = MessageType.TOOL_RESULT
    tool: str
    step_id: str
    success: bool
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    verification_passed: bool = False

class ProgressMessage(Message):
    """Message containing progress updates"""
    type: MessageType = MessageType.PROGRESS
    step: str
    percent: int
    status: str
    description: str

class UserInputRequestMessage(Message):
    """Message requesting user input/approval"""
    type: MessageType = MessageType.USER_INPUT_REQUEST
    step_id: str
    question: str
    options: List[str]
    timeout: Optional[int] = None

class ErrorMessage(Message):
    """Message containing error information"""
    type: MessageType = MessageType.ERROR
    error_type: str
    message: str
    step_id: Optional[str] = None
    retry_available: bool = False

class ProcessPausedMessage(Message):
    """Message indicating process is paused"""
    type: MessageType = MessageType.PROCESS_PAUSED
    step_id: str
    reason: str
    resume_options: List[str]

class WorkflowCompleteMessage(Message):
    """Message indicating workflow is complete"""
    type: MessageType = MessageType.WORKFLOW_COMPLETE
    success: bool
    summary: str
    output_files: List[str]
    total_steps: int
    completed_steps: int

class MessageHandler:
    """
    Handles real-time message communication between orchestrator and frontend
    Implements dual-response pattern and streaming updates
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.message_queue: List[Message] = []
        self.subscribers: List[Callable[[Message], None]] = []
        self.user_responses: Dict[str, Any] = {}
        self.pending_requests: Dict[str, asyncio.Event] = {}
        
        logger.info("Message handler initialized", session_id=session_id)
    
    def subscribe(self, callback: Callable[[Message], None]):
        """Subscribe to message updates"""
        self.subscribers.append(callback)
        logger.info("New subscriber added", subscriber_count=len(self.subscribers))
    
    def unsubscribe(self, callback: Callable[[Message], None]):
        """Unsubscribe from message updates"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
            logger.info("Subscriber removed", subscriber_count=len(self.subscribers))
    
    async def send_message(self, message: Message):
        """Send a message to all subscribers"""
        try:
            # Add to queue
            self.message_queue.append(message)
            
            # Notify all subscribers
            for subscriber in self.subscribers:
                try:
                    await asyncio.create_task(self._notify_subscriber(subscriber, message))
                except Exception as e:
                    logger.error("Failed to notify subscriber", error=str(e))
            
            logger.info("Message sent", 
                       message_type=message.type.value,
                       session_id=message.session_id)
            
        except Exception as e:
            logger.error("Failed to send message", error=str(e))
    
    async def _notify_subscriber(self, subscriber: Callable[[Message], None], message: Message):
        """Notify a single subscriber"""
        if asyncio.iscoroutinefunction(subscriber):
            await subscriber(message)
        else:
            subscriber(message)
    
    # Convenience methods for different message types
    
    async def send_ai_message(self, content: str, step_id: Optional[str] = None):
        """Send AI agent message"""
        message = AIMessage(
            timestamp=datetime.now(),
            session_id=self.session_id,
            data={},
            content=content,
            step_id=step_id
        )
        await self.send_message(message)
    
    async def send_tool_call(self, tool: str, args: Dict[str, Any], step_id: str, description: str):
        """Send tool call message"""
        message = ToolCallMessage(
            timestamp=datetime.now(),
            session_id=self.session_id,
            data={},
            tool=tool,
            args=args,
            step_id=step_id,
            description=description
        )
        await self.send_message(message)
    
    async def send_tool_result(self, tool: str, step_id: str, success: bool, 
                              output: Optional[Dict[str, Any]] = None, 
                              error: Optional[str] = None,
                              verification_passed: bool = False):
        """Send tool result message"""
        message = ToolResultMessage(
            timestamp=datetime.now(),
            session_id=self.session_id,
            data={},
            tool=tool,
            step_id=step_id,
            success=success,
            output=output,
            error=error,
            verification_passed=verification_passed
        )
        await self.send_message(message)
    
    async def send_progress(self, step: str, percent: int, status: str, description: str):
        """Send progress update"""
        message = ProgressMessage(
            timestamp=datetime.now(),
            session_id=self.session_id,
            data={},
            step=step,
            percent=percent,
            status=status,
            description=description
        )
        await self.send_message(message)
    
    async def send_user_input_request(self, step_id: str, question: str, 
                                     options: List[str], timeout: Optional[int] = None):
        """Send user input request and wait for response"""
        message = UserInputRequestMessage(
            timestamp=datetime.now(),
            session_id=self.session_id,
            data={},
            step_id=step_id,
            question=question,
            options=options,
            timeout=timeout
        )
        
        # Create event for waiting
        event = asyncio.Event()
        self.pending_requests[step_id] = event
        
        await self.send_message(message)
        
        # Wait for response
        try:
            if timeout:
                await asyncio.wait_for(event.wait(), timeout=timeout)
            else:
                await event.wait()
        except asyncio.TimeoutError:
            logger.warning("User input request timed out", step_id=step_id)
            return None
        finally:
            if step_id in self.pending_requests:
                del self.pending_requests[step_id]
        
        return self.user_responses.get(step_id)
    
    async def send_error(self, error_type: str, message: str, step_id: Optional[str] = None, 
                        retry_available: bool = False):
        """Send error message"""
        error_msg = ErrorMessage(
            timestamp=datetime.now(),
            session_id=self.session_id,
            data={},
            error_type=error_type,
            message=message,
            step_id=step_id,
            retry_available=retry_available
        )
        await self.send_message(error_msg)
    
    async def send_process_paused(self, step_id: str, reason: str, resume_options: List[str]):
        """Send process paused message"""
        message = ProcessPausedMessage(
            timestamp=datetime.now(),
            session_id=self.session_id,
            data={},
            step_id=step_id,
            reason=reason,
            resume_options=resume_options
        )
        await self.send_message(message)
    
    async def send_workflow_complete(self, success: bool, summary: str, 
                                   output_files: List[str], total_steps: int, completed_steps: int):
        """Send workflow complete message"""
        message = WorkflowCompleteMessage(
            timestamp=datetime.now(),
            session_id=self.session_id,
            data={},
            success=success,
            summary=summary,
            output_files=output_files,
            total_steps=total_steps,
            completed_steps=completed_steps
        )
        await self.send_message(message)
    
    # User response handling
    
    async def handle_user_response(self, step_id: str, response: Any):
        """Handle user response to input request"""
        self.user_responses[step_id] = response
        
        # Signal waiting task
        if step_id in self.pending_requests:
            self.pending_requests[step_id].set()
        
        logger.info("User response received", step_id=step_id, response=response)
    
    # Dual-response pattern implementation
    
    async def send_dual_response(self, user_message: str, tool_call: Optional[Dict[str, Any]] = None):
        """
        Send dual response: user-facing message + backend tool call
        This implements the dual-response pattern from our plan
        """
        # Send user message
        await self.send_ai_message(user_message)
        
        # Send tool call if present
        if tool_call:
            await self.send_tool_call(
                tool=tool_call["tool"],
                args=tool_call["args"],
                step_id=tool_call["step_id"],
                description=tool_call["description"]
            )
    
    # Utility methods
    
    def get_message_history(self) -> List[Message]:
        """Get all messages sent in this session"""
        return self.message_queue.copy()
    
    def get_last_message(self) -> Optional[Message]:
        """Get the last message sent"""
        return self.message_queue[-1] if self.message_queue else None
    
    def clear_history(self):
        """Clear message history"""
        self.message_queue.clear()
        logger.info("Message history cleared")
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get session information"""
        return {
            "session_id": self.session_id,
            "message_count": len(self.message_queue),
            "subscriber_count": len(self.subscribers),
            "pending_requests": list(self.pending_requests.keys()),
            "user_responses": list(self.user_responses.keys())
        } 