"""
Professional Dependency Injection System
Clean architecture with proper dependency management
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Type, TypeVar, Optional, Callable
from dataclasses import dataclass
import inspect
import asyncio

T = TypeVar('T')

# ============================================================================
# SERVICE INTERFACES
# ============================================================================

class SessionRepository(ABC):
    """Abstract session repository interface"""
    
    @abstractmethod
    async def create_session(self, user_id: str, **kwargs) -> str:
        """Create a new session"""
        pass
    
    @abstractmethod
    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session by ID"""
        pass
    
    @abstractmethod
    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> None:
        """Update session"""
        pass
    
    @abstractmethod
    async def delete_session(self, session_id: str) -> None:
        """Delete session"""
        pass

class MessageRepository(ABC):
    """Abstract message repository interface"""
    
    @abstractmethod
    async def store_message(self, session_id: str, message_id: str, **kwargs) -> None:
        """Store a message"""
        pass
    
    @abstractmethod
    async def get_messages(self, session_id: str, limit: int = 100) -> list:
        """Get messages for a session"""
        pass
    
    @abstractmethod
    async def update_message(self, session_id: str, message_id: str, **kwargs) -> None:
        """Update a message"""
        pass

class WorkflowRepository(ABC):
    """Abstract workflow repository interface"""
    
    @abstractmethod
    async def create_workflow(self, workflow_id: str, session_id: str, **kwargs) -> None:
        """Create a workflow"""
        pass
    
    @abstractmethod
    async def update_workflow(self, workflow_id: str, **kwargs) -> None:
        """Update a workflow"""
        pass
    
    @abstractmethod
    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow by ID"""
        pass

class AIService(ABC):
    """Abstract AI service interface"""
    
    @abstractmethod
    async def generate_response(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Generate AI response"""
        pass
    
    @abstractmethod
    async def analyze_intent(self, message: str) -> Dict[str, Any]:
        """Analyze message intent"""
        pass

class WebSocketManager(ABC):
    """Abstract WebSocket manager interface"""
    
    @abstractmethod
    async def broadcast_to_session(self, session_id: str, message: Dict[str, Any]) -> None:
        """Broadcast message to session"""
        pass
    
    @abstractmethod
    async def send_to_user(self, user_id: str, message: Dict[str, Any]) -> None:
        """Send message to specific user"""
        pass

# ============================================================================
# CONCRETE IMPLEMENTATIONS
# ============================================================================

class InMemorySessionRepository(SessionRepository):
    """In-memory session repository implementation"""
    
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
    
    async def create_session(self, user_id: str, **kwargs) -> str:
        """Create a new session"""
        import uuid
        session_id = str(uuid.uuid4())
        
        self._sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": "2024-01-01T00:00:00Z",
            "status": "active",
            **kwargs
        }
        
        return session_id
    
    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session by ID"""
        if session_id not in self._sessions:
            raise ValueError(f"Session not found: {session_id}")
        return self._sessions[session_id]
    
    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> None:
        """Update session"""
        if session_id not in self._sessions:
            raise ValueError(f"Session not found: {session_id}")
        
        self._sessions[session_id].update(updates)
    
    async def delete_session(self, session_id: str) -> None:
        """Delete session"""
        if session_id in self._sessions:
            del self._sessions[session_id]

class InMemoryMessageRepository(MessageRepository):
    """In-memory message repository implementation"""
    
    def __init__(self):
        self._messages: Dict[str, list] = {}
    
    async def store_message(self, session_id: str, message_id: str, **kwargs) -> None:
        """Store a message"""
        if session_id not in self._messages:
            self._messages[session_id] = []
        
        message = {
            "message_id": message_id,
            "session_id": session_id,
            "timestamp": "2024-01-01T00:00:00Z",
            **kwargs
        }
        
        self._messages[session_id].append(message)
    
    async def get_messages(self, session_id: str, limit: int = 100) -> list:
        """Get messages for a session"""
        return self._messages.get(session_id, [])[-limit:]
    
    async def update_message(self, session_id: str, message_id: str, **kwargs) -> None:
        """Update a message"""
        if session_id not in self._messages:
            return
        
        for message in self._messages[session_id]:
            if message["message_id"] == message_id:
                message.update(kwargs)
                break

class GeminiAIService(AIService):
    """Gemini AI service implementation"""
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-exp"):
        self.api_key = api_key
        self.model = model
    
    async def generate_response(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Generate AI response using Gemini"""
        # This would contain the actual Gemini API call
        return f"AI Response to: {prompt}"
    
    async def analyze_intent(self, message: str) -> Dict[str, Any]:
        """Analyze message intent"""
        # This would contain intent analysis logic
        return {
            "intent": "video_creation",
            "confidence": 0.9,
            "entities": []
        }

class WebSocketManagerImpl(WebSocketManager):
    """WebSocket manager implementation"""
    
    def __init__(self):
        self._connections: Dict[str, Any] = {}
    
    async def broadcast_to_session(self, session_id: str, message: Dict[str, Any]) -> None:
        """Broadcast message to session"""
        # This would contain actual WebSocket broadcasting logic
        print(f"Broadcasting to session {session_id}: {message}")
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]) -> None:
        """Send message to specific user"""
        # This would contain actual WebSocket sending logic
        print(f"Sending to user {user_id}: {message}")

# ============================================================================
# DEPENDENCY INJECTION CONTAINER
# ============================================================================

@dataclass
class ServiceRegistration:
    """Service registration information"""
    interface: Type
    implementation: Type
    singleton: bool = True
    factory: Optional[Callable] = None
    dependencies: Dict[str, Type] = None

class DependencyContainer:
    """Dependency injection container"""
    
    def __init__(self):
        self._services: Dict[Type, ServiceRegistration] = {}
        self._singletons: Dict[Type, Any] = {}
    
    def register(self, interface: Type[T], implementation: Type[T], 
                singleton: bool = True, factory: Optional[Callable] = None,
                dependencies: Dict[str, Type] = None) -> None:
        """Register a service"""
        self._services[interface] = ServiceRegistration(
            interface=interface,
            implementation=implementation,
            singleton=singleton,
            factory=factory,
            dependencies=dependencies
        )
    
    def register_instance(self, interface: Type[T], instance: T) -> None:
        """Register a singleton instance"""
        self._singletons[interface] = instance
    
    async def resolve(self, interface: Type[T]) -> T:
        """Resolve a service"""
        # Check if we have a singleton instance
        if interface in self._singletons:
            return self._singletons[interface]
        
        # Check if we have a registration
        if interface not in self._services:
            raise ValueError(f"No registration found for {interface}")
        
        registration = self._services[interface]
        
        # Create instance
        if registration.factory:
            instance = await registration.factory(self)
        else:
            instance = await self._create_instance(registration)
        
        # Store singleton if needed
        if registration.singleton:
            self._singletons[interface] = instance
        
        return instance
    
    async def _create_instance(self, registration: ServiceRegistration) -> Any:
        """Create an instance of a service"""
        implementation = registration.implementation
        
        # Get constructor parameters
        sig = inspect.signature(implementation.__init__)
        params = {}
        
        for name, param in sig.parameters.items():
            if name == 'self':
                continue
            
            # Check if we have a dependency mapping
            if registration.dependencies and name in registration.dependencies:
                dependency_type = registration.dependencies[name]
                params[name] = await self.resolve(dependency_type)
            else:
                # Try to infer the type from the parameter annotation
                if param.annotation != inspect.Parameter.empty:
                    params[name] = await self.resolve(param.annotation)
                else:
                    # Use default value if available
                    if param.default != inspect.Parameter.empty:
                        params[name] = param.default
                    else:
                        raise ValueError(f"Cannot resolve parameter {name} for {implementation}")
        
        return implementation(**params)
    
    def clear(self) -> None:
        """Clear all registrations and singletons"""
        self._services.clear()
        self._singletons.clear()

# ============================================================================
# APPLICATION CONTEXT
# ============================================================================

class ApplicationContext:
    """Application context with dependency injection"""
    
    def __init__(self):
        self.container = DependencyContainer()
        self._setup_services()
    
    def _setup_services(self) -> None:
        """Setup service registrations"""
        # Register repositories
        self.container.register(SessionRepository, InMemorySessionRepository)
        self.container.register(MessageRepository, InMemoryMessageRepository)
        self.container.register(WorkflowRepository, InMemorySessionRepository)  # Reuse for demo
        
        # Register services
        self.container.register(AIService, GeminiAIService, 
                              dependencies={"api_key": str, "model": str})
        self.container.register(WebSocketManager, WebSocketManagerImpl)
        
        # Register configuration
        self.container.register_instance(str, "your-gemini-api-key")
        self.container.register_instance(str, "gemini-2.0-flash-exp")
    
    async def get_service(self, service_type: Type[T]) -> T:
        """Get a service from the container"""
        return await self.container.resolve(service_type)

# ============================================================================
# SERVICE LAYER
# ============================================================================

class SessionService:
    """Session service with dependency injection"""
    
    def __init__(self, session_repository: SessionRepository, 
                 websocket_manager: WebSocketManager):
        self.session_repository = session_repository
        self.websocket_manager = websocket_manager
    
    async def create_session(self, user_id: str, prompt: str) -> str:
        """Create a new session"""
        session_id = await self.session_repository.create_session(
            user_id=user_id,
            initial_prompt=prompt
        )
        
        # Notify via WebSocket
        await self.websocket_manager.broadcast_to_session(session_id, {
            "type": "session.created",
            "session_id": session_id
        })
        
        return session_id
    
    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session information"""
        return await self.session_repository.get_session(session_id)

class MessageService:
    """Message service with dependency injection"""
    
    def __init__(self, message_repository: MessageRepository,
                 ai_service: AIService,
                 websocket_manager: WebSocketManager):
        self.message_repository = message_repository
        self.ai_service = ai_service
        self.websocket_manager = websocket_manager
    
    async def process_message(self, session_id: str, content: str) -> str:
        """Process a user message"""
        import uuid
        message_id = str(uuid.uuid4())
        
        # Store message
        await self.message_repository.store_message(
            session_id=session_id,
            message_id=message_id,
            content=content,
            message_type="user_message"
        )
        
        # Generate AI response
        response = await self.ai_service.generate_response(content)
        
        # Store response
        response_id = str(uuid.uuid4())
        await self.message_repository.store_message(
            session_id=session_id,
            message_id=response_id,
            content=response,
            message_type="ai_message"
        )
        
        # Notify via WebSocket
        await self.websocket_manager.broadcast_to_session(session_id, {
            "type": "message.processed",
            "message_id": message_id,
            "response": response
        })
        
        return response_id

# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================

async def create_ai_service(container: DependencyContainer) -> AIService:
    """Factory function for creating AI service"""
    api_key = await container.resolve(str)
    model = await container.resolve(str)
    return GeminiAIService(api_key, model)

# ============================================================================
# USAGE EXAMPLE
# ============================================================================

class ApplicationService:
    """Application service using dependency injection"""
    
    def __init__(self, app_context: ApplicationContext):
        self.app_context = app_context
        self._session_service: Optional[SessionService] = None
        self._message_service: Optional[MessageService] = None
    
    async def initialize(self) -> None:
        """Initialize services"""
        # Resolve dependencies
        session_repository = await self.app_context.get_service(SessionRepository)
        message_repository = await self.app_context.get_service(MessageRepository)
        ai_service = await self.app_context.get_service(AIService)
        websocket_manager = await self.app_context.get_service(WebSocketManager)
        
        # Create services
        self._session_service = SessionService(session_repository, websocket_manager)
        self._message_service = MessageService(message_repository, ai_service, websocket_manager)
    
    async def create_session(self, user_id: str, prompt: str) -> str:
        """Create a session"""
        if not self._session_service:
            await self.initialize()
        
        return await self._session_service.create_session(user_id, prompt)
    
    async def process_message(self, session_id: str, content: str) -> str:
        """Process a message"""
        if not self._message_service:
            await self.initialize()
        
        return await self._message_service.process_message(session_id, content)

# ============================================================================
# SETUP AND USAGE
# ============================================================================

async def setup_application() -> ApplicationService:
    """Setup the application with dependency injection"""
    # Create application context
    app_context = ApplicationContext()
    
    # Register factory function
    app_context.container.register(AIService, GeminiAIService, factory=create_ai_service)
    
    # Create application service
    app_service = ApplicationService(app_context)
    await app_service.initialize()
    
    return app_service

# Example usage
async def main():
    """Example usage of the dependency injection system"""
    app = await setup_application()
    
    # Create a session
    session_id = await app.create_session("user123", "Create a video about space")
    print(f"Created session: {session_id}")
    
    # Process a message
    message_id = await app.process_message(session_id, "Make it cinematic")
    print(f"Processed message: {message_id}")

if __name__ == "__main__":
    asyncio.run(main()) 