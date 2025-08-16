"""
Event-Driven Architecture
Professional decoupling of components through events
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import uuid

# ============================================================================
# EVENT DEFINITIONS
# ============================================================================

@dataclass
class Event:
    """Base event class"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SessionCreatedEvent(Event):
    """Event fired when a session is created"""
    event_type: str = "session.created"
    session_id: str = ""
    user_id: str = ""
    initial_prompt: str = ""
    style: str = "cinematic"
    length: str = "medium"
    tone: str = "professional"

@dataclass
class MessageReceivedEvent(Event):
    """Event fired when a message is received"""
    event_type: str = "message.received"
    session_id: str = ""
    message_id: str = ""
    content: str = ""
    message_type: str = "user_message"

@dataclass
class MessageProcessedEvent(Event):
    """Event fired when a message is processed"""
    event_type: str = "message.processed"
    session_id: str = ""
    message_id: str = ""
    response_content: str = ""
    processing_time: float = 0.0

@dataclass
class WorkflowStartedEvent(Event):
    """Event fired when a workflow starts"""
    event_type: str = "workflow.started"
    session_id: str = ""
    workflow_id: str = ""
    steps: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class WorkflowStepCompletedEvent(Event):
    """Event fired when a workflow step completes"""
    event_type: str = "workflow.step.completed"
    session_id: str = ""
    workflow_id: str = ""
    step_id: str = ""
    step_result: Dict[str, Any] = field(default_factory=dict)
    duration: float = 0.0

@dataclass
class WorkflowCompletedEvent(Event):
    """Event fired when a workflow completes"""
    event_type: str = "workflow.completed"
    session_id: str = ""
    workflow_id: str = ""
    final_result: Dict[str, Any] = field(default_factory=dict)
    total_duration: float = 0.0

@dataclass
class ErrorOccurredEvent(Event):
    """Event fired when an error occurs"""
    event_type: str = "error.occurred"
    session_id: Optional[str] = None
    error_type: str = ""
    error_message: str = ""
    stack_trace: Optional[str] = None

# ============================================================================
# EVENT HANDLERS
# ============================================================================

class EventHandler(ABC):
    """Abstract base class for event handlers"""
    
    @abstractmethod
    async def handle(self, event: Event) -> None:
        """Handle an event"""
        pass

class SessionEventHandler(EventHandler):
    """Handler for session-related events"""
    
    def __init__(self, session_repository, websocket_manager):
        self.session_repository = session_repository
        self.websocket_manager = websocket_manager
    
    async def handle(self, event: Event) -> None:
        """Handle session events"""
        if event.event_type == "session.created":
            await self._handle_session_created(event)
        elif event.event_type == "session.updated":
            await self._handle_session_updated(event)
    
    async def _handle_session_created(self, event: SessionCreatedEvent) -> None:
        """Handle session created event"""
        # Update session repository
        await self.session_repository.update_session(event.session_id, {
            "status": "active",
            "created_at": event.timestamp,
            "user_id": event.user_id
        })
        
        # Notify connected clients
        await self.websocket_manager.broadcast_to_session(
            event.session_id,
            {
                "type": "session.created",
                "session_id": event.session_id,
                "timestamp": event.timestamp.isoformat()
            }
        )

class MessageEventHandler(EventHandler):
    """Handler for message-related events"""
    
    def __init__(self, message_repository, websocket_manager):
        self.message_repository = message_repository
        self.websocket_manager = websocket_manager
    
    async def handle(self, event: Event) -> None:
        """Handle message events"""
        if event.event_type == "message.received":
            await self._handle_message_received(event)
        elif event.event_type == "message.processed":
            await self._handle_message_processed(event)
    
    async def _handle_message_received(self, event: MessageReceivedEvent) -> None:
        """Handle message received event"""
        # Store message
        await self.message_repository.store_message(
            session_id=event.session_id,
            message_id=event.message_id,
            content=event.content,
            message_type=event.message_type,
            timestamp=event.timestamp
        )
        
        # Notify clients
        await self.websocket_manager.broadcast_to_session(
            event.session_id,
            {
                "type": "message.received",
                "message_id": event.message_id,
                "content": event.content,
                "timestamp": event.timestamp.isoformat()
            }
        )
    
    async def _handle_message_processed(self, event: MessageProcessedEvent) -> None:
        """Handle message processed event"""
        # Update message with response
        await self.message_repository.update_message(
            session_id=event.session_id,
            message_id=event.message_id,
            response_content=event.response_content,
            processing_time=event.processing_time
        )
        
        # Notify clients
        await self.websocket_manager.broadcast_to_session(
            event.session_id,
            {
                "type": "message.processed",
                "message_id": event.message_id,
                "response_content": event.response_content,
                "processing_time": event.processing_time,
                "timestamp": event.timestamp.isoformat()
            }
        )

class WorkflowEventHandler(EventHandler):
    """Handler for workflow-related events"""
    
    def __init__(self, workflow_repository, websocket_manager):
        self.workflow_repository = workflow_repository
        self.websocket_manager = websocket_manager
    
    async def handle(self, event: Event) -> None:
        """Handle workflow events"""
        if event.event_type == "workflow.started":
            await self._handle_workflow_started(event)
        elif event.event_type == "workflow.step.completed":
            await self._handle_workflow_step_completed(event)
        elif event.event_type == "workflow.completed":
            await self._handle_workflow_completed(event)
    
    async def _handle_workflow_started(self, event: WorkflowStartedEvent) -> None:
        """Handle workflow started event"""
        # Update workflow repository
        await self.workflow_repository.create_workflow(
            workflow_id=event.workflow_id,
            session_id=event.session_id,
            steps=event.steps,
            started_at=event.timestamp
        )
        
        # Notify clients
        await self.websocket_manager.broadcast_to_session(
            event.session_id,
            {
                "type": "workflow.started",
                "workflow_id": event.workflow_id,
                "steps": event.steps,
                "timestamp": event.timestamp.isoformat()
            }
        )
    
    async def _handle_workflow_step_completed(self, event: WorkflowStepCompletedEvent) -> None:
        """Handle workflow step completed event"""
        # Update workflow repository
        await self.workflow_repository.update_step(
            workflow_id=event.workflow_id,
            step_id=event.step_id,
            result=event.step_result,
            duration=event.duration,
            completed_at=event.timestamp
        )
        
        # Notify clients
        await self.websocket_manager.broadcast_to_session(
            event.session_id,
            {
                "type": "workflow.step.completed",
                "workflow_id": event.workflow_id,
                "step_id": event.step_id,
                "result": event.step_result,
                "duration": event.duration,
                "timestamp": event.timestamp.isoformat()
            }
        )

class ErrorEventHandler(EventHandler):
    """Handler for error events"""
    
    def __init__(self, error_repository, websocket_manager, logger):
        self.error_repository = error_repository
        self.websocket_manager = websocket_manager
        self.logger = logger
    
    async def handle(self, event: Event) -> None:
        """Handle error events"""
        # Log error
        self.logger.error(f"Error occurred: {event.error_type} - {event.error_message}")
        
        # Store error
        await self.error_repository.store_error(
            session_id=event.session_id,
            error_type=event.error_type,
            error_message=event.error_message,
            stack_trace=event.stack_trace,
            timestamp=event.timestamp
        )
        
        # Notify clients if session_id is available
        if event.session_id:
            await self.websocket_manager.broadcast_to_session(
                event.session_id,
                {
                    "type": "error.occurred",
                    "error_type": event.error_type,
                    "error_message": event.error_message,
                    "timestamp": event.timestamp.isoformat()
                }
            )

# ============================================================================
# EVENT BUS
# ============================================================================

class EventBus:
    """Event bus for publishing and subscribing to events"""
    
    def __init__(self):
        self._subscribers: Dict[str, List[EventHandler]] = {}
        self._middleware: List[Callable] = []
    
    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe to an event type"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
    
    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe from an event type"""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h != handler
            ]
    
    def add_middleware(self, middleware: Callable) -> None:
        """Add middleware to the event bus"""
        self._middleware.append(middleware)
    
    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers"""
        # Apply middleware
        for middleware in self._middleware:
            event = await middleware(event)
        
        # Get subscribers for this event type
        handlers = self._subscribers.get(event.event_type, [])
        
        # Execute handlers concurrently
        tasks = [handler.handle(event) for handler in handlers]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def publish_batch(self, events: List[Event]) -> None:
        """Publish multiple events"""
        for event in events:
            await self.publish(event)

# ============================================================================
# EVENT STORE
# ============================================================================

class EventStore:
    """Event store for persistence and replay"""
    
    def __init__(self, storage_backend):
        self.storage_backend = storage_backend
    
    async def store_event(self, event: Event) -> None:
        """Store an event"""
        event_data = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "timestamp": event.timestamp.isoformat(),
            "session_id": event.session_id,
            "user_id": event.user_id,
            "data": event.data,
            "metadata": event.metadata
        }
        
        await self.storage_backend.store_event(event_data)
    
    async def get_events(self, session_id: str, limit: int = 100) -> List[Event]:
        """Get events for a session"""
        events_data = await self.storage_backend.get_events(session_id, limit)
        
        events = []
        for event_data in events_data:
            event = Event(
                event_id=event_data["event_id"],
                event_type=event_data["event_type"],
                timestamp=datetime.fromisoformat(event_data["timestamp"]),
                session_id=event_data["session_id"],
                user_id=event_data["user_id"],
                data=event_data["data"],
                metadata=event_data["metadata"]
            )
            events.append(event)
        
        return events
    
    async def replay_events(self, session_id: str, event_handler: EventHandler) -> None:
        """Replay events for a session"""
        events = await self.get_events(session_id)
        
        for event in events:
            await event_handler.handle(event)

# ============================================================================
# USAGE EXAMPLE
# ============================================================================

class EventDrivenApplication:
    """Example of using event-driven architecture"""
    
    def __init__(self, event_bus: EventBus, event_store: EventStore):
        self.event_bus = event_bus
        self.event_store = event_store
    
    async def create_session(self, user_id: str, prompt: str) -> str:
        """Create a session using events"""
        session_id = str(uuid.uuid4())
        
        # Create and publish event
        event = SessionCreatedEvent(
            session_id=session_id,
            user_id=user_id,
            initial_prompt=prompt
        )
        
        # Store event
        await self.event_store.store_event(event)
        
        # Publish event
        await self.event_bus.publish(event)
        
        return session_id
    
    async def process_message(self, session_id: str, content: str) -> str:
        """Process a message using events"""
        message_id = str(uuid.uuid4())
        
        # Create message received event
        received_event = MessageReceivedEvent(
            session_id=session_id,
            message_id=message_id,
            content=content
        )
        
        # Store and publish event
        await self.event_store.store_event(received_event)
        await self.event_bus.publish(received_event)
        
        # Simulate processing
        await asyncio.sleep(0.1)
        
        # Create message processed event
        processed_event = MessageProcessedEvent(
            session_id=session_id,
            message_id=message_id,
            response_content=f"Processed: {content}",
            processing_time=0.1
        )
        
        # Store and publish event
        await self.event_store.store_event(processed_event)
        await self.event_bus.publish(processed_event)
        
        return message_id 