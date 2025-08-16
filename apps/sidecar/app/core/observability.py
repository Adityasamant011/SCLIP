"""
Professional Observability System
Metrics, Tracing, and Structured Logging
"""

import time
import json
import logging
import traceback
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import asynccontextmanager, contextmanager
import asyncio
import uuid

# ============================================================================
# METRICS
# ============================================================================

class MetricsCollector(ABC):
    """Abstract metrics collector"""
    
    @abstractmethod
    def increment_counter(self, name: str, value: int = 1, labels: Dict[str, str] = None) -> None:
        """Increment a counter metric"""
        pass
    
    @abstractmethod
    def record_gauge(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """Record a gauge metric"""
        pass
    
    @abstractmethod
    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """Record a histogram metric"""
        pass
    
    @abstractmethod
    def record_timing(self, name: str, duration: float, labels: Dict[str, str] = None) -> None:
        """Record a timing metric"""
        pass

class PrometheusMetricsCollector(MetricsCollector):
    """Prometheus-style metrics collector"""
    
    def __init__(self):
        self._counters: Dict[str, Dict[str, int]] = {}
        self._gauges: Dict[str, Dict[str, float]] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._timings: Dict[str, List[float]] = {}
    
    def increment_counter(self, name: str, value: int = 1, labels: Dict[str, str] = None) -> None:
        """Increment a counter metric"""
        label_key = self._get_label_key(labels)
        if name not in self._counters:
            self._counters[name] = {}
        self._counters[name][label_key] = self._counters[name].get(label_key, 0) + value
    
    def record_gauge(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """Record a gauge metric"""
        label_key = self._get_label_key(labels)
        if name not in self._gauges:
            self._gauges[name] = {}
        self._gauges[name][label_key] = value
    
    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """Record a histogram metric"""
        if name not in self._histograms:
            self._histograms[name] = []
        self._histograms[name].append(value)
    
    def record_timing(self, name: str, duration: float, labels: Dict[str, str] = None) -> None:
        """Record a timing metric"""
        if name not in self._timings:
            self._timings[name] = []
        self._timings[name].append(duration)
    
    def _get_label_key(self, labels: Dict[str, str] = None) -> str:
        """Convert labels to a key string"""
        if not labels:
            return "default"
        return json.dumps(labels, sort_keys=True)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics"""
        return {
            "counters": self._counters,
            "gauges": self._gauges,
            "histograms": self._histograms,
            "timings": self._timings
        }

# ============================================================================
# TRACING
# ============================================================================

@dataclass
class Span:
    """Represents a span in a trace"""
    span_id: str
    trace_id: str
    name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    parent_span_id: Optional[str] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None

class Tracer(ABC):
    """Abstract tracer"""
    
    @abstractmethod
    def start_span(self, name: str, parent_span_id: Optional[str] = None) -> Span:
        """Start a new span"""
        pass
    
    @abstractmethod
    def end_span(self, span: Span, error: Optional[str] = None) -> None:
        """End a span"""
        pass
    
    @abstractmethod
    def add_tag(self, span: Span, key: str, value: Any) -> None:
        """Add a tag to a span"""
        pass
    
    @abstractmethod
    def add_log(self, span: Span, message: str, data: Dict[str, Any] = None) -> None:
        """Add a log to a span"""
        pass

class JaegerTracer(Tracer):
    """Jaeger-compatible tracer"""
    
    def __init__(self):
        self._spans: List[Span] = []
        self._current_spans: Dict[str, Span] = {}
    
    def start_span(self, name: str, parent_span_id: Optional[str] = None) -> Span:
        """Start a new span"""
        span_id = str(uuid.uuid4())
        trace_id = parent_span_id or str(uuid.uuid4())
        
        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            name=name,
            start_time=datetime.now(),
            parent_span_id=parent_span_id
        )
        
        self._current_spans[span_id] = span
        return span
    
    def end_span(self, span: Span, error: Optional[str] = None) -> None:
        """End a span"""
        span.end_time = datetime.now()
        span.error = error
        
        self._spans.append(span)
        if span.span_id in self._current_spans:
            del self._current_spans[span.span_id]
    
    def add_tag(self, span: Span, key: str, value: Any) -> None:
        """Add a tag to a span"""
        span.tags[key] = value
    
    def add_log(self, span: Span, message: str, data: Dict[str, Any] = None) -> None:
        """Add a log to a span"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "data": data or {}
        }
        span.logs.append(log_entry)
    
    def get_traces(self) -> List[Dict[str, Any]]:
        """Get all traces"""
        traces = {}
        for span in self._spans:
            if span.trace_id not in traces:
                traces[span.trace_id] = []
            traces[span.trace_id].append({
                "span_id": span.span_id,
                "name": span.name,
                "start_time": span.start_time.isoformat(),
                "end_time": span.end_time.isoformat() if span.end_time else None,
                "parent_span_id": span.parent_span_id,
                "tags": span.tags,
                "logs": span.logs,
                "error": span.error
            })
        
        return list(traces.values())

# ============================================================================
# STRUCTURED LOGGING
# ============================================================================

class StructuredLogger:
    """Structured logger with correlation IDs"""
    
    def __init__(self, name: str, metrics_collector: MetricsCollector = None):
        self.name = name
        self.metrics_collector = metrics_collector
        self.logger = logging.getLogger(name)
        self._correlation_id = None
    
    def set_correlation_id(self, correlation_id: str) -> None:
        """Set correlation ID for this logger instance"""
        self._correlation_id = correlation_id
    
    def _log(self, level: str, message: str, **kwargs) -> None:
        """Internal logging method"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "logger": self.name,
            "message": message,
            "correlation_id": self._correlation_id,
            **kwargs
        }
        
        # Convert to JSON for structured logging
        log_json = json.dumps(log_entry)
        
        if level == "DEBUG":
            self.logger.debug(log_json)
        elif level == "INFO":
            self.logger.info(log_json)
        elif level == "WARNING":
            self.logger.warning(log_json)
        elif level == "ERROR":
            self.logger.error(log_json)
        elif level == "CRITICAL":
            self.logger.critical(log_json)
        
        # Record metrics
        if self.metrics_collector:
            self.metrics_collector.increment_counter(
                "log_entries_total",
                labels={"level": level, "logger": self.name}
            )
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message"""
        self._log("DEBUG", message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message"""
        self._log("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message"""
        self._log("WARNING", message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message"""
        self._log("ERROR", message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message"""
        self._log("CRITICAL", message, **kwargs)

# ============================================================================
# OBSERVABILITY CONTEXT
# ============================================================================

class ObservabilityContext:
    """Context manager for observability"""
    
    def __init__(self, metrics_collector: MetricsCollector, tracer: Tracer, logger: StructuredLogger):
        self.metrics_collector = metrics_collector
        self.tracer = tracer
        self.logger = logger
        self._current_span: Optional[Span] = None
    
    @contextmanager
    def trace_span(self, name: str, tags: Dict[str, Any] = None):
        """Context manager for tracing spans"""
        span = self.tracer.start_span(name)
        self._current_span = span
        
        if tags:
            for key, value in tags.items():
                self.tracer.add_tag(span, key, value)
        
        start_time = time.time()
        
        try:
            yield span
        except Exception as e:
            self.tracer.end_span(span, error=str(e))
            raise
        finally:
            duration = time.time() - start_time
            self.tracer.end_span(span)
            
            # Record timing metric
            self.metrics_collector.record_timing(
                f"span_duration_{name}",
                duration,
                tags
            )
    
    @asynccontextmanager
    async def async_trace_span(self, name: str, tags: Dict[str, Any] = None):
        """Async context manager for tracing spans"""
        span = self.tracer.start_span(name)
        self._current_span = span
        
        if tags:
            for key, value in tags.items():
                self.tracer.add_tag(span, key, value)
        
        start_time = time.time()
        
        try:
            yield span
        except Exception as e:
            self.tracer.end_span(span, error=str(e))
            raise
        finally:
            duration = time.time() - start_time
            self.tracer.end_span(span)
            
            # Record timing metric
            self.metrics_collector.record_timing(
                f"span_duration_{name}",
                duration,
                tags
            )
    
    def log_with_context(self, level: str, message: str, **kwargs) -> None:
        """Log with current context"""
        if self._current_span:
            kwargs["span_id"] = self._current_span.span_id
            kwargs["trace_id"] = self._current_span.trace_id
        
        if level == "DEBUG":
            self.logger.debug(message, **kwargs)
        elif level == "INFO":
            self.logger.info(message, **kwargs)
        elif level == "WARNING":
            self.logger.warning(message, **kwargs)
        elif level == "ERROR":
            self.logger.error(message, **kwargs)
        elif level == "CRITICAL":
            self.logger.critical(message, **kwargs)
    
    def record_metric(self, name: str, value: float, metric_type: str = "gauge", labels: Dict[str, str] = None) -> None:
        """Record a metric"""
        if metric_type == "counter":
            self.metrics_collector.increment_counter(name, int(value), labels)
        elif metric_type == "gauge":
            self.metrics_collector.record_gauge(name, value, labels)
        elif metric_type == "histogram":
            self.metrics_collector.record_histogram(name, value, labels)
        elif metric_type == "timing":
            self.metrics_collector.record_timing(name, value, labels)

# ============================================================================
# DECORATORS
# ============================================================================

def trace_function(name: str = None, tags: Dict[str, Any] = None):
    """Decorator to trace function execution"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Get observability context from first argument if it's a method
            obs_context = None
            if args and hasattr(args[0], '_obs_context'):
                obs_context = args[0]._obs_context
            
            if obs_context:
                with obs_context.trace_span(name or func.__name__, tags):
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator

def async_trace_function(name: str = None, tags: Dict[str, Any] = None):
    """Decorator to trace async function execution"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get observability context from first argument if it's a method
            obs_context = None
            if args and hasattr(args[0], '_obs_context'):
                obs_context = args[0]._obs_context
            
            if obs_context:
                async with obs_context.async_trace_span(name or func.__name__, tags):
                    return await func(*args, **kwargs)
            else:
                return await func(*args, **kwargs)
        return wrapper
    return decorator

def monitor_function(metric_name: str = None, labels: Dict[str, str] = None):
    """Decorator to monitor function execution with metrics"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Get observability context from first argument if it's a method
            obs_context = None
            if args and hasattr(args[0], '_obs_context'):
                obs_context = args[0]._obs_context
            
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                if obs_context:
                    duration = time.time() - start_time
                    obs_context.record_metric(
                        metric_name or f"{func.__name__}_duration",
                        duration,
                        "timing",
                        labels
                    )
                    obs_context.record_metric(
                        metric_name or f"{func.__name__}_success",
                        1,
                        "counter",
                        labels
                    )
                
                return result
            except Exception as e:
                if obs_context:
                    obs_context.record_metric(
                        metric_name or f"{func.__name__}_errors",
                        1,
                        "counter",
                        labels
                    )
                raise
        
        async def async_wrapper(*args, **kwargs):
            # Get observability context from first argument if it's a method
            obs_context = None
            if args and hasattr(args[0], '_obs_context'):
                obs_context = args[0]._obs_context
            
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                if obs_context:
                    duration = time.time() - start_time
                    obs_context.record_metric(
                        metric_name or f"{func.__name__}_duration",
                        duration,
                        "timing",
                        labels
                    )
                    obs_context.record_metric(
                        metric_name or f"{func.__name__}_success",
                        1,
                        "counter",
                        labels
                    )
                
                return result
            except Exception as e:
                if obs_context:
                    obs_context.record_metric(
                        metric_name or f"{func.__name__}_errors",
                        1,
                        "counter",
                        labels
                    )
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return wrapper
    return decorator

# ============================================================================
# USAGE EXAMPLE
# ============================================================================

class ObservableService:
    """Example service with observability"""
    
    def __init__(self):
        # Initialize observability components
        self.metrics_collector = PrometheusMetricsCollector()
        self.tracer = JaegerTracer()
        self.logger = StructuredLogger("ObservableService", self.metrics_collector)
        self.obs_context = ObservabilityContext(
            self.metrics_collector,
            self.tracer,
            self.logger
        )
        self._obs_context = self.obs_context  # For decorators
    
    @trace_function("process_message")
    @monitor_function("message_processing")
    def process_message(self, message: str) -> str:
        """Process a message with observability"""
        self.obs_context.log_with_context("INFO", "Processing message", message=message)
        
        # Simulate processing
        time.sleep(0.1)
        
        result = f"Processed: {message}"
        self.obs_context.log_with_context("INFO", "Message processed", result=result)
        
        return result
    
    @async_trace_function("async_process_message")
    @monitor_function("async_message_processing")
    async def async_process_message(self, message: str) -> str:
        """Process a message asynchronously with observability"""
        self.obs_context.log_with_context("INFO", "Processing message async", message=message)
        
        # Simulate async processing
        await asyncio.sleep(0.1)
        
        result = f"Async processed: {message}"
        self.obs_context.log_with_context("INFO", "Message processed async", result=result)
        
        return result
    
    def get_observability_data(self) -> Dict[str, Any]:
        """Get all observability data"""
        return {
            "metrics": self.metrics_collector.get_metrics(),
            "traces": self.tracer.get_traces()
        } 