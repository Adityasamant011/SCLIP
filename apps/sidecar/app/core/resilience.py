"""
Professional Resilience System
Circuit breakers, retries, and graceful degradation
"""

import asyncio
import time
import random
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import functools

T = TypeVar('T')

# ============================================================================
# CIRCUIT BREAKER
# ============================================================================

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered

@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5          # Number of failures before opening
    recovery_timeout: float = 60.0      # Time to wait before half-open (seconds)
    expected_exception: type = Exception  # Exception type to consider as failure
    success_threshold: int = 2          # Successes needed to close circuit
    timeout: float = 30.0               # Request timeout

class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_state_change = datetime.now()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._set_half_open()
            else:
                raise CircuitBreakerOpenError(f"Circuit breaker '{self.name}' is OPEN")
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout
            )
            
            self._on_success()
            return result
            
        except asyncio.TimeoutError:
            self._on_failure("Timeout")
            raise
        except self.config.expected_exception as e:
            self._on_failure(str(e))
            raise
        except Exception as e:
            # Unexpected exceptions don't count as failures
            raise
    
    def _on_success(self) -> None:
        """Handle successful execution"""
        self.failure_count = 0
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self._set_closed()
    
    def _on_failure(self, error: str) -> None:
        """Handle failed execution"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self._set_open()
        elif self.state == CircuitState.HALF_OPEN:
            self._set_open()
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit"""
        if not self.last_failure_time:
            return False
        
        return (datetime.now() - self.last_failure_time).total_seconds() >= self.config.recovery_timeout
    
    def _set_open(self) -> None:
        """Set circuit to open state"""
        self.state = CircuitState.OPEN
        self.last_state_change = datetime.now()
        self.success_count = 0
    
    def _set_half_open(self) -> None:
        """Set circuit to half-open state"""
        self.state = CircuitState.HALF_OPEN
        self.last_state_change = datetime.now()
        self.success_count = 0
    
    def _set_closed(self) -> None:
        """Set circuit to closed state"""
        self.state = CircuitState.CLOSED
        self.last_state_change = datetime.now()
        self.failure_count = 0
        self.success_count = 0
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_state_change": self.last_state_change.isoformat()
        }

class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open"""
    pass

# ============================================================================
# RETRY MECHANISM
# ============================================================================

@dataclass
class RetryConfig:
    """Retry configuration"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple = (Exception,)

class RetryHandler:
    """Retry mechanism with exponential backoff"""
    
    def __init__(self, config: RetryConfig):
        self.config = config
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic"""
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                return await func(*args, **kwargs)
            except self.config.retryable_exceptions as e:
                last_exception = e
                
                if attempt == self.config.max_attempts:
                    raise last_exception
                
                # Calculate delay with exponential backoff
                delay = self._calculate_delay(attempt)
                await asyncio.sleep(delay)
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt"""
        delay = self.config.base_delay * (self.config.exponential_base ** (attempt - 1))
        delay = min(delay, self.config.max_delay)
        
        if self.config.jitter:
            # Add jitter to prevent thundering herd
            delay *= (0.5 + random.random() * 0.5)
        
        return delay

# ============================================================================
# BULKHEAD PATTERN
# ============================================================================

class Bulkhead:
    """Bulkhead pattern for resource isolation"""
    
    def __init__(self, name: str, max_concurrent: int = 10, max_queue_size: int = 100):
        self.name = name
        self.max_concurrent = max_concurrent
        self.max_queue_size = max_queue_size
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.queue = asyncio.Queue(maxsize=max_queue_size)
        self.active_tasks = 0
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with bulkhead protection"""
        try:
            async with self.semaphore:
                self.active_tasks += 1
                try:
                    return await func(*args, **kwargs)
                finally:
                    self.active_tasks -= 1
        except asyncio.QueueFull:
            raise BulkheadFullError(f"Bulkhead '{self.name}' queue is full")
    
    def get_status(self) -> Dict[str, Any]:
        """Get bulkhead status"""
        return {
            "name": self.name,
            "max_concurrent": self.max_concurrent,
            "active_tasks": self.active_tasks,
            "queue_size": self.queue.qsize(),
            "max_queue_size": self.max_queue_size
        }

class BulkheadFullError(Exception):
    """Exception raised when bulkhead is full"""
    pass

# ============================================================================
# TIMEOUT HANDLER
# ============================================================================

class TimeoutHandler:
    """Timeout handler for async operations"""
    
    def __init__(self, default_timeout: float = 30.0):
        self.default_timeout = default_timeout
    
    async def execute(self, func: Callable, timeout: Optional[float] = None, 
                     *args, **kwargs) -> Any:
        """Execute function with timeout"""
        timeout = timeout or self.default_timeout
        
        try:
            return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Operation timed out after {timeout} seconds")

# ============================================================================
# FALLBACK HANDLER
# ============================================================================

class FallbackHandler:
    """Fallback handler for graceful degradation"""
    
    def __init__(self, fallback_func: Optional[Callable] = None, 
                 fallback_value: Any = None):
        self.fallback_func = fallback_func
        self.fallback_value = fallback_value
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with fallback"""
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if self.fallback_func:
                return await self.fallback_func(*args, **kwargs)
            elif self.fallback_value is not None:
                return self.fallback_value
            else:
                raise

# ============================================================================
# RESILIENCE MANAGER
# ============================================================================

class ResilienceManager:
    """Combined resilience manager"""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.bulkheads: Dict[str, Bulkhead] = {}
        self.retry_handlers: Dict[str, RetryHandler] = {}
        self.timeout_handler = TimeoutHandler()
        self.fallback_handlers: Dict[str, FallbackHandler] = {}
    
    def add_circuit_breaker(self, name: str, config: CircuitBreakerConfig) -> CircuitBreaker:
        """Add a circuit breaker"""
        circuit_breaker = CircuitBreaker(name, config)
        self.circuit_breakers[name] = circuit_breaker
        return circuit_breaker
    
    def add_bulkhead(self, name: str, max_concurrent: int = 10, 
                    max_queue_size: int = 100) -> Bulkhead:
        """Add a bulkhead"""
        bulkhead = Bulkhead(name, max_concurrent, max_queue_size)
        self.bulkheads[name] = bulkhead
        return bulkhead
    
    def add_retry_handler(self, name: str, config: RetryConfig) -> RetryHandler:
        """Add a retry handler"""
        retry_handler = RetryHandler(config)
        self.retry_handlers[name] = retry_handler
        return retry_handler
    
    def add_fallback_handler(self, name: str, fallback_func: Optional[Callable] = None,
                           fallback_value: Any = None) -> FallbackHandler:
        """Add a fallback handler"""
        fallback_handler = FallbackHandler(fallback_func, fallback_value)
        self.fallback_handlers[name] = fallback_handler
        return fallback_handler
    
    async def execute(self, func: Callable, 
                     circuit_breaker_name: Optional[str] = None,
                     bulkhead_name: Optional[str] = None,
                     retry_name: Optional[str] = None,
                     fallback_name: Optional[str] = None,
                     timeout: Optional[float] = None,
                     *args, **kwargs) -> Any:
        """Execute function with resilience patterns"""
        
        # Apply fallback first (outermost)
        if fallback_name and fallback_name in self.fallback_handlers:
            fallback_handler = self.fallback_handlers[fallback_name]
            func = lambda *a, **kw: fallback_handler.execute(func, *a, **kw)
        
        # Apply timeout
        if timeout:
            func = lambda *a, **kw: self.timeout_handler.execute(func, timeout, *a, **kw)
        
        # Apply retry
        if retry_name and retry_name in self.retry_handlers:
            retry_handler = self.retry_handlers[retry_name]
            func = lambda *a, **kw: retry_handler.execute(func, *a, **kw)
        
        # Apply bulkhead
        if bulkhead_name and bulkhead_name in self.bulkheads:
            bulkhead = self.bulkheads[bulkhead_name]
            func = lambda *a, **kw: bulkhead.execute(func, *a, **kw)
        
        # Apply circuit breaker (innermost)
        if circuit_breaker_name and circuit_breaker_name in self.circuit_breakers:
            circuit_breaker = self.circuit_breakers[circuit_breaker_name]
            return await circuit_breaker.call(func, *args, **kwargs)
        
        # Execute without circuit breaker
        return await func(*args, **kwargs)
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all resilience components"""
        return {
            "circuit_breakers": {
                name: cb.get_status() for name, cb in self.circuit_breakers.items()
            },
            "bulkheads": {
                name: bh.get_status() for name, bh in self.bulkheads.items()
            }
        }

# ============================================================================
# DECORATORS
# ============================================================================

def resilient(circuit_breaker_name: Optional[str] = None,
             bulkhead_name: Optional[str] = None,
             retry_name: Optional[str] = None,
             fallback_name: Optional[str] = None,
             timeout: Optional[float] = None):
    """Decorator for applying resilience patterns"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get resilience manager from first argument if it's a method
            resilience_manager = None
            if args and hasattr(args[0], '_resilience_manager'):
                resilience_manager = args[0]._resilience_manager
            
            if resilience_manager:
                return await resilience_manager.execute(
                    func,
                    circuit_breaker_name=circuit_breaker_name,
                    bulkhead_name=bulkhead_name,
                    retry_name=retry_name,
                    fallback_name=fallback_name,
                    timeout=timeout,
                    *args, **kwargs
                )
            else:
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator

# ============================================================================
# USAGE EXAMPLE
# ============================================================================

class ResilientService:
    """Example service with resilience patterns"""
    
    def __init__(self):
        self.resilience_manager = ResilienceManager()
        self._resilience_manager = self.resilience_manager  # For decorators
        
        # Setup resilience patterns
        self._setup_resilience()
    
    def _setup_resilience(self) -> None:
        """Setup resilience patterns"""
        # Circuit breaker for external API calls
        self.resilience_manager.add_circuit_breaker(
            "external_api",
            CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=30.0,
                expected_exception=Exception
            )
        )
        
        # Bulkhead for concurrent operations
        self.resilience_manager.add_bulkhead("concurrent_ops", max_concurrent=5)
        
        # Retry handler for transient failures
        self.resilience_manager.add_retry_handler(
            "transient_failures",
            RetryConfig(
                max_attempts=3,
                base_delay=1.0,
                exponential_base=2.0
            )
        )
        
        # Fallback handler
        self.resilience_manager.add_fallback_handler(
            "api_fallback",
            fallback_value={"status": "degraded", "message": "Service temporarily unavailable"}
        )
    
    @resilient(
        circuit_breaker_name="external_api",
        bulkhead_name="concurrent_ops",
        retry_name="transient_failures",
        fallback_name="api_fallback",
        timeout=10.0
    )
    async def call_external_api(self, endpoint: str) -> Dict[str, Any]:
        """Call external API with full resilience"""
        # Simulate external API call
        await asyncio.sleep(0.1)
        
        # Simulate occasional failures
        if random.random() < 0.3:
            raise Exception("External API error")
        
        return {"status": "success", "data": f"Response from {endpoint}"}
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get service status including resilience patterns"""
        return {
            "service": "ResilientService",
            "status": "healthy",
            "resilience": self.resilience_manager.get_status()
        }

# Example usage
async def main():
    """Example usage of resilience patterns"""
    service = ResilientService()
    
    # Make resilient API calls
    for i in range(10):
        try:
            result = await service.call_external_api(f"/api/endpoint/{i}")
            print(f"Call {i}: {result}")
        except Exception as e:
            print(f"Call {i}: Failed - {e}")
        
        await asyncio.sleep(0.5)
    
    # Get service status
    status = await service.get_service_status()
    print(f"Service status: {status}")

if __name__ == "__main__":
    asyncio.run(main()) 