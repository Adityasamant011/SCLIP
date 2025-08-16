"""
Strongly-Typed, Unified Messaging Layer for Sclip
Provides type-safe communication between frontend and backend
"""
import json
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from pydantic import BaseModel, Field, validator

from .logger import get_logger

logger = get_logger(__name__)

class MessageType(Enum):
    """Message types for real-time communication"""
    AI_MESSAGE = "ai_message"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    PROGRESS = "progress"
    USER_INPUT_REQUEST = "user_input_request"
    PROCESS_PAUSED = "process_paused"
    ERROR = "error"
    SESSION_UPDATE = "session_update"
    FILE_UPDATE = "file_update"
    PREFERENCE_UPDATE = "preference_update"

class MessageStatus(Enum):
    """Message status for tracking"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"

class BaseMessage(BaseModel):
    """Base message class with common fields"""
    message_id: str = Field(description="Unique message identifier")
    message_type: MessageType = Field(description="Type of message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")
    session_id: Optional[str] = Field(default=None, description="Associated session ID")
    user_id: Optional[str] = Field(default=None, description="Associated user ID")
    status: MessageStatus = Field(default=MessageStatus.PENDING, description="Message status")
    version: str = Field(default="1.0.0", description="Message protocol version")

class AIMessage(BaseMessage):
    """AI agent's user-facing message"""
    content: str = Field(description="AI message content")
    step: Optional[str] = Field(default=None, description="Current workflow step")
    confidence: Optional[float] = Field(default=None, description="AI confidence level (0-1)")
    suggestions: Optional[List[str]] = Field(default=None, description="Suggested actions")
    
    def __init__(self, **data):
        data['message_type'] = MessageType.AI_MESSAGE
        super().__init__(**data)

class ToolCall(BaseMessage):
    """Tool execution call"""
    tool_name: str = Field(description="Name of the tool being called")
    tool_args: Dict[str, Any] = Field(description="Tool arguments")
    step_id: str = Field(description="Workflow step identifier")
    timeout: Optional[float] = Field(default=300.0, description="Tool timeout in seconds")
    
    def __init__(self, **data):
        data['message_type'] = MessageType.TOOL_CALL
        super().__init__(**data)

class ToolResult(BaseMessage):
    """Tool execution result"""
    tool_name: str = Field(description="Name of the tool that was called")
    step_id: str = Field(description="Workflow step identifier")
    success: bool = Field(description="Whether tool execution was successful")
    output: Optional[Dict[str, Any]] = Field(default=None, description="Tool output")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    execution_time: float = Field(description="Tool execution time in seconds")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    
    def __init__(self, **data):
        data['message_type'] = MessageType.TOOL_RESULT
        super().__init__(**data)

class Progress(BaseMessage):
    """Progress update"""
    step: str = Field(description="Current step name")
    percent: float = Field(description="Progress percentage (0-100)")
    status: str = Field(description="Current status")
    estimated_remaining: Optional[float] = Field(default=None, description="Estimated time remaining")
    details: Optional[str] = Field(default=None, description="Additional progress details")
    
    def __init__(self, **data):
        data['message_type'] = MessageType.PROGRESS
        super().__init__(**data)

class UserInputRequest(BaseMessage):
    """Request for user input/approval"""
    step_id: str = Field(description="Step requiring approval")
    request_type: str = Field(description="Type of request (approval, input, choice)")
    prompt: str = Field(description="User prompt")
    options: Optional[List[Dict[str, Any]]] = Field(default=None, description="Available options")
    timeout: Optional[float] = Field(default=None, description="Request timeout")
    required: bool = Field(default=True, description="Whether input is required")
    
    def __init__(self, **data):
        data['message_type'] = MessageType.USER_INPUT_REQUEST
        super().__init__(**data)

class ProcessPaused(BaseMessage):
    """Process paused notification"""
    step: str = Field(description="Step where process was paused")
    reason: str = Field(description="Reason for pausing")
    resume_available: bool = Field(default=True, description="Whether process can be resumed")
    user_actions_required: Optional[List[str]] = Field(default=None, description="Actions user can take")
    
    def __init__(self, **data):
        data['message_type'] = MessageType.PROCESS_PAUSED
        super().__init__(**data)

class ErrorMessage(BaseMessage):
    """Error message"""
    error_code: str = Field(description="Error code")
    error_message: str = Field(description="Human-readable error message")
    error_details: Optional[Dict[str, Any]] = Field(default=None, description="Detailed error information")
    recoverable: bool = Field(default=True, description="Whether error is recoverable")
    suggested_actions: Optional[List[str]] = Field(default=None, description="Suggested recovery actions")
    
    def __init__(self, **data):
        data['message_type'] = MessageType.ERROR
        super().__init__(**data)

class SessionUpdate(BaseMessage):
    """Session state update"""
    session_status: str = Field(description="Current session status")
    current_step: Optional[str] = Field(default=None, description="Current workflow step")
    completed_steps: List[str] = Field(default_factory=list, description="Completed steps")
    remaining_steps: List[str] = Field(default_factory=list, description="Remaining steps")
    session_duration: Optional[float] = Field(default=None, description="Session duration in seconds")
    
    def __init__(self, **data):
        data['message_type'] = MessageType.SESSION_UPDATE
        super().__init__(**data)

class FileUpdate(BaseMessage):
    """File update notification"""
    file_path: str = Field(description="Path to the file")
    file_type: str = Field(description="Type of file")
    action: str = Field(description="Action performed (created, updated, deleted)")
    file_size: Optional[int] = Field(default=None, description="File size in bytes")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="File metadata")
    
    def __init__(self, **data):
        data['message_type'] = MessageType.FILE_UPDATE
        super().__init__(**data)

class PreferenceUpdate(BaseMessage):
    """User preference update"""
    preference_type: str = Field(description="Type of preference updated")
    old_value: Optional[Any] = Field(default=None, description="Previous value")
    new_value: Any = Field(description="New value")
    source: str = Field(description="Source of update (user, inference, system)")
    
    def __init__(self, **data):
        data['message_type'] = MessageType.PREFERENCE_UPDATE
        super().__init__(**data)

class MessageFactory:
    """Factory for creating typed messages"""
    
    @staticmethod
    def create_ai_message(content: str, session_id: str, **kwargs) -> AIMessage:
        """Create an AI message"""
        return AIMessage(
            message_id=f"ai_{datetime.now().timestamp()}",
            content=content,
            session_id=session_id,
            **kwargs
        )
    
    @staticmethod
    def create_tool_call(tool_name: str, tool_args: Dict[str, Any], step_id: str, session_id: str, **kwargs) -> ToolCall:
        """Create a tool call message"""
        return ToolCall(
            message_id=f"tool_call_{datetime.now().timestamp()}",
            tool_name=tool_name,
            tool_args=tool_args,
            step_id=step_id,
            session_id=session_id,
            **kwargs
        )
    
    @staticmethod
    def create_tool_result(tool_name: str, step_id: str, success: bool, session_id: str, **kwargs) -> ToolResult:
        """Create a tool result message"""
        # Extract execution_time from kwargs to avoid duplication
        execution_time = kwargs.pop('execution_time', 0.0)
        
        return ToolResult(
            message_id=f"tool_result_{datetime.now().timestamp()}",
            tool_name=tool_name,
            step_id=step_id,
            success=success,
            session_id=session_id,
            execution_time=execution_time,
            **kwargs
        )
    
    @staticmethod
    def create_progress(step: str, percent: float, status: str, session_id: str, **kwargs) -> Progress:
        """Create a progress message"""
        return Progress(
            message_id=f"progress_{datetime.now().timestamp()}",
            step=step,
            percent=percent,
            status=status,
            session_id=session_id,
            **kwargs
        )
    
    @staticmethod
    def create_user_input_request(step_id: str, request_type: str, prompt: str, session_id: str, **kwargs) -> UserInputRequest:
        """Create a user input request message"""
        return UserInputRequest(
            message_id=f"user_input_{datetime.now().timestamp()}",
            step_id=step_id,
            request_type=request_type,
            prompt=prompt,
            session_id=session_id,
            **kwargs
        )
    
    @staticmethod
    def create_process_paused(step: str, reason: str, session_id: str, **kwargs) -> ProcessPaused:
        """Create a process paused message"""
        return ProcessPaused(
            message_id=f"paused_{datetime.now().timestamp()}",
            step=step,
            reason=reason,
            session_id=session_id,
            **kwargs
        )
    
    @staticmethod
    def create_error(error_code: str, error_message: str, session_id: str, **kwargs) -> ErrorMessage:
        """Create an error message"""
        return ErrorMessage(
            message_id=f"error_{datetime.now().timestamp()}",
            error_code=error_code,
            error_message=error_message,
            session_id=session_id,
            **kwargs
        )
    
    @staticmethod
    def create_session_update(session_status: str, session_id: str, **kwargs) -> SessionUpdate:
        """Create a session update message"""
        return SessionUpdate(
            message_id=f"session_{datetime.now().timestamp()}",
            session_status=session_status,
            session_id=session_id,
            **kwargs
        )
    
    @staticmethod
    def create_file_update(file_path: str, file_type: str, action: str, session_id: str, **kwargs) -> FileUpdate:
        """Create a file update message"""
        return FileUpdate(
            message_id=f"file_{datetime.now().timestamp()}",
            file_path=file_path,
            file_type=file_type,
            action=action,
            session_id=session_id,
            **kwargs
        )
    
    @staticmethod
    def create_preference_update(preference_type: str, new_value: Any, user_id: str, **kwargs) -> PreferenceUpdate:
        """Create a preference update message"""
        return PreferenceUpdate(
            message_id=f"pref_{datetime.now().timestamp()}",
            preference_type=preference_type,
            new_value=new_value,
            user_id=user_id,
            **kwargs
        )

class MessageSerializer:
    """Serialize and deserialize messages"""
    
    @staticmethod
    def serialize(message: BaseMessage) -> str:
        """Serialize a message to JSON string"""
        try:
            return message.json()
        except Exception as e:
            logger.error(f"Failed to serialize message: {e}")
            raise
    
    @staticmethod
    def deserialize(message_json: str) -> BaseMessage:
        """Deserialize a JSON string to a message"""
        try:
            data = json.loads(message_json)
            message_type = MessageType(data.get("message_type"))
            
            # Map message type to class
            message_classes = {
                MessageType.AI_MESSAGE: AIMessage,
                MessageType.TOOL_CALL: ToolCall,
                MessageType.TOOL_RESULT: ToolResult,
                MessageType.PROGRESS: Progress,
                MessageType.USER_INPUT_REQUEST: UserInputRequest,
                MessageType.PROCESS_PAUSED: ProcessPaused,
                MessageType.ERROR: ErrorMessage,
                MessageType.SESSION_UPDATE: SessionUpdate,
                MessageType.FILE_UPDATE: FileUpdate,
                MessageType.PREFERENCE_UPDATE: PreferenceUpdate
            }
            
            message_class = message_classes.get(message_type)
            if not message_class:
                raise ValueError(f"Unknown message type: {message_type}")
            
            return message_class(**data)
            
        except Exception as e:
            logger.error(f"Failed to deserialize message: {e}")
            raise

class MessageValidator:
    """Validate message structure and content"""
    
    @staticmethod
    def validate_message(message: BaseMessage) -> bool:
        """Validate a message"""
        try:
            # Basic validation
            if not message.message_id:
                return False
            
            if not message.message_type:
                return False
            
            # Type-specific validation
            if isinstance(message, ToolCall):
                return MessageValidator._validate_tool_call(message)
            elif isinstance(message, ToolResult):
                return MessageValidator._validate_tool_result(message)
            elif isinstance(message, Progress):
                return MessageValidator._validate_progress(message)
            elif isinstance(message, ErrorMessage):
                return MessageValidator._validate_error(message)
            
            return True
            
        except Exception as e:
            logger.error(f"Message validation failed: {e}")
            return False
    
    @staticmethod
    def _validate_tool_call(message: ToolCall) -> bool:
        """Validate tool call message"""
        return bool(message.tool_name and message.tool_args is not None)
    
    @staticmethod
    def _validate_tool_result(message: ToolResult) -> bool:
        """Validate tool result message"""
        return bool(message.tool_name and message.step_id)
    
    @staticmethod
    def _validate_progress(message: Progress) -> bool:
        """Validate progress message"""
        return 0 <= message.percent <= 100
    
    @staticmethod
    def _validate_error(message: ErrorMessage) -> bool:
        """Validate error message"""
        return bool(message.error_code and message.error_message) 