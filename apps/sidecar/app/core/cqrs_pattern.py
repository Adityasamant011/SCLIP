"""
Command Query Responsibility Segregation (CQRS) Pattern
Professional separation of read and write operations
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio
from enum import Enum

# ============================================================================
# COMMANDS (Write Operations)
# ============================================================================

@dataclass
class CreateSessionCommand:
    """Command to create a new session"""
    user_id: str
    initial_prompt: str
    style: str = "cinematic"
    length: str = "medium"
    tone: str = "professional"

@dataclass
class ProcessMessageCommand:
    """Command to process a user message"""
    session_id: str
    content: str
    message_type: str = "user_message"
    timestamp: datetime = None

@dataclass
class ExecuteWorkflowCommand:
    """Command to execute a workflow"""
    session_id: str
    workflow_plan: Dict[str, Any]
    user_context: Dict[str, Any]

@dataclass
class UpdateSessionCommand:
    """Command to update session state"""
    session_id: str
    updates: Dict[str, Any]

# ============================================================================
# QUERIES (Read Operations)
# ============================================================================

@dataclass
class GetSessionQuery:
    """Query to get session information"""
    session_id: str

@dataclass
class GetMessagesQuery:
    """Query to get messages for a session"""
    session_id: str
    limit: int = 100
    offset: int = 0
    message_type: Optional[str] = None

@dataclass
class GetWorkflowStatusQuery:
    """Query to get workflow status"""
    session_id: str

@dataclass
class ListSessionsQuery:
    """Query to list user sessions"""
    user_id: str
    limit: int = 50
    offset: int = 0
    status: Optional[str] = None

# ============================================================================
# COMMAND HANDLERS
# ============================================================================

class CommandHandler(ABC):
    """Abstract base class for command handlers"""
    
    @abstractmethod
    async def handle(self, command: Any) -> Any:
        """Handle a command and return result"""
        pass

class CreateSessionHandler(CommandHandler):
    """Handler for creating sessions"""
    
    def __init__(self, session_repository, event_bus):
        self.session_repository = session_repository
        self.event_bus = event_bus
    
    async def handle(self, command: CreateSessionCommand) -> str:
        """Create a new session"""
        session_id = await self.session_repository.create_session(
            user_id=command.user_id,
            initial_prompt=command.initial_prompt,
            style=command.style,
            length=command.length,
            tone=command.tone
        )
        
        # Publish session created event
        await self.event_bus.publish("session.created", {
            "session_id": session_id,
            "user_id": command.user_id,
            "timestamp": datetime.now()
        })
        
        return session_id

class ProcessMessageHandler(CommandHandler):
    """Handler for processing messages"""
    
    def __init__(self, message_repository, workflow_orchestrator, event_bus):
        self.message_repository = message_repository
        self.workflow_orchestrator = workflow_orchestrator
        self.event_bus = event_bus
    
    async def handle(self, command: ProcessMessageCommand) -> str:
        """Process a user message"""
        # Store message
        message_id = await self.message_repository.store_message(
            session_id=command.session_id,
            content=command.content,
            message_type=command.message_type,
            timestamp=command.timestamp or datetime.now()
        )
        
        # Trigger workflow orchestration
        await self.workflow_orchestrator.process_message(
            session_id=command.session_id,
            message_id=message_id,
            content=command.content
        )
        
        # Publish message processed event
        await self.event_bus.publish("message.processed", {
            "session_id": command.session_id,
            "message_id": message_id,
            "timestamp": datetime.now()
        })
        
        return message_id

# ============================================================================
# QUERY HANDLERS
# ============================================================================

class QueryHandler(ABC):
    """Abstract base class for query handlers"""
    
    @abstractmethod
    async def handle(self, query: Any) -> Any:
        """Handle a query and return result"""
        pass

class GetSessionHandler(QueryHandler):
    """Handler for getting session information"""
    
    def __init__(self, session_repository):
        self.session_repository = session_repository
    
    async def handle(self, query: GetSessionQuery) -> Dict[str, Any]:
        """Get session information"""
        return await self.session_repository.get_session(query.session_id)

class GetMessagesHandler(QueryHandler):
    """Handler for getting messages"""
    
    def __init__(self, message_repository):
        self.message_repository = message_repository
    
    async def handle(self, query: GetMessagesQuery) -> List[Dict[str, Any]]:
        """Get messages for a session"""
        return await self.message_repository.get_messages(
            session_id=query.session_id,
            limit=query.limit,
            offset=query.offset,
            message_type=query.message_type
        )

# ============================================================================
# COMMAND/QUERY BUS
# ============================================================================

class CommandBus:
    """Command bus for dispatching commands to handlers"""
    
    def __init__(self):
        self._handlers: Dict[type, CommandHandler] = {}
    
    def register_handler(self, command_type: type, handler: CommandHandler):
        """Register a command handler"""
        self._handlers[command_type] = handler
    
    async def dispatch(self, command: Any) -> Any:
        """Dispatch a command to its handler"""
        handler = self._handlers.get(type(command))
        if not handler:
            raise ValueError(f"No handler registered for command type: {type(command)}")
        
        return await handler.handle(command)

class QueryBus:
    """Query bus for dispatching queries to handlers"""
    
    def __init__(self):
        self._handlers: Dict[type, QueryHandler] = {}
    
    def register_handler(self, query_type: type, handler: QueryHandler):
        """Register a query handler"""
        self._handlers[query_type] = handler
    
    async def dispatch(self, query: Any) -> Any:
        """Dispatch a query to its handler"""
        handler = self._handlers.get(type(query))
        if not handler:
            raise ValueError(f"No handler registered for query type: {type(query)}")
        
        return await handler.handle(query)

# ============================================================================
# USAGE EXAMPLE
# ============================================================================

class ApplicationService:
    """Application service using CQRS pattern"""
    
    def __init__(self, command_bus: CommandBus, query_bus: QueryBus):
        self.command_bus = command_bus
        self.query_bus = query_bus
    
    async def create_session(self, user_id: str, prompt: str) -> str:
        """Create a new session"""
        command = CreateSessionCommand(
            user_id=user_id,
            initial_prompt=prompt
        )
        return await self.command_bus.dispatch(command)
    
    async def process_message(self, session_id: str, content: str) -> str:
        """Process a user message"""
        command = ProcessMessageCommand(
            session_id=session_id,
            content=content
        )
        return await self.command_bus.dispatch(command)
    
    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session information"""
        query = GetSessionQuery(session_id=session_id)
        return await self.query_bus.dispatch(query)
    
    async def get_messages(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get messages for a session"""
        query = GetMessagesQuery(session_id=session_id, limit=limit)
        return await self.query_bus.dispatch(query) 