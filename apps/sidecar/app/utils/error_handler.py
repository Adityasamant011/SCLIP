"""
Unified Error Handling & User Feedback System for Sclip
Provides consistent error handling and user-friendly error messages
"""
import traceback
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from datetime import datetime

from .logger import get_logger
from .messaging import MessageFactory, ErrorMessage

logger = get_logger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories for classification"""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RESOURCE_NOT_FOUND = "resource_not_found"
    NETWORK = "network"
    DATABASE = "database"
    TOOL_EXECUTION = "tool_execution"
    ORCHESTRATOR = "orchestrator"
    FILE_OPERATION = "file_operation"
    SYSTEM = "system"
    UNKNOWN = "unknown"

class ErrorCode(Enum):
    """Standard error codes"""
    # Validation errors
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"
    
    # Authentication errors
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    
    # Resource errors
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    RESOURCE_UNAVAILABLE = "RESOURCE_UNAVAILABLE"
    
    # Network errors
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
    NETWORK_CONNECTION_FAILED = "NETWORK_CONNECTION_FAILED"
    API_RATE_LIMIT = "API_RATE_LIMIT"
    
    # Database errors
    DATABASE_CONNECTION_FAILED = "DATABASE_CONNECTION_FAILED"
    DATABASE_QUERY_FAILED = "DATABASE_QUERY_FAILED"
    DATABASE_TRANSACTION_FAILED = "DATABASE_TRANSACTION_FAILED"
    
    # Tool execution errors
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    TOOL_EXECUTION_FAILED = "TOOL_EXECUTION_FAILED"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    TOOL_VALIDATION_FAILED = "TOOL_VALIDATION_FAILED"
    
    # Orchestrator errors
    ORCHESTRATOR_STATE_ERROR = "ORCHESTRATOR_STATE_ERROR"
    WORKFLOW_STEP_FAILED = "WORKFLOW_STEP_FAILED"
    SESSION_MANAGEMENT_ERROR = "SESSION_MANAGEMENT_ERROR"
    
    # File operation errors
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_PERMISSION_DENIED = "FILE_PERMISSION_DENIED"
    FILE_CORRUPTED = "FILE_CORRUPTED"
    DISK_SPACE_FULL = "DISK_SPACE_FULL"
    
    # System errors
    SYSTEM_RESOURCE_EXHAUSTED = "SYSTEM_RESOURCE_EXHAUSTED"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"

class SclipError(Exception):
    """Base exception class for Sclip"""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = True,
        suggested_actions: Optional[List[str]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.recoverable = recoverable
        self.suggested_actions = suggested_actions or []
        self.timestamp = datetime.now()
        self.traceback = traceback.format_exc()
        
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary"""
        return {
            "message": self.message,
            "error_code": self.error_code.value,
            "category": self.category.value,
            "severity": self.severity.value,
            "details": self.details,
            "recoverable": self.recoverable,
            "suggested_actions": self.suggested_actions,
            "timestamp": self.timestamp.isoformat(),
            "traceback": self.traceback
        }
    
    def to_error_message(self, session_id: str) -> ErrorMessage:
        """Convert to ErrorMessage for frontend"""
        return MessageFactory.create_error(
            error_code=self.error_code.value,
            error_message=self.message,
            session_id=session_id,
            error_details=self.details,
            recoverable=self.recoverable,
            suggested_actions=self.suggested_actions
        )

class ErrorHandler:
    """Centralized error handling system"""
    
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.error_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
        
        # Error code to category mapping
        self.error_mappings = {
            ErrorCode.INVALID_INPUT: ErrorCategory.VALIDATION,
            ErrorCode.MISSING_REQUIRED_FIELD: ErrorCategory.VALIDATION,
            ErrorCode.INVALID_FORMAT: ErrorCategory.VALIDATION,
            ErrorCode.UNAUTHORIZED: ErrorCategory.AUTHENTICATION,
            ErrorCode.INVALID_CREDENTIALS: ErrorCategory.AUTHENTICATION,
            ErrorCode.SESSION_EXPIRED: ErrorCategory.AUTHENTICATION,
            ErrorCode.RESOURCE_NOT_FOUND: ErrorCategory.RESOURCE_NOT_FOUND,
            ErrorCode.RESOURCE_ALREADY_EXISTS: ErrorCategory.RESOURCE_NOT_FOUND,
            ErrorCode.RESOURCE_UNAVAILABLE: ErrorCategory.RESOURCE_NOT_FOUND,
            ErrorCode.NETWORK_TIMEOUT: ErrorCategory.NETWORK,
            ErrorCode.NETWORK_CONNECTION_FAILED: ErrorCategory.NETWORK,
            ErrorCode.API_RATE_LIMIT: ErrorCategory.NETWORK,
            ErrorCode.DATABASE_CONNECTION_FAILED: ErrorCategory.DATABASE,
            ErrorCode.DATABASE_QUERY_FAILED: ErrorCategory.DATABASE,
            ErrorCode.DATABASE_TRANSACTION_FAILED: ErrorCategory.DATABASE,
            ErrorCode.TOOL_NOT_FOUND: ErrorCategory.TOOL_EXECUTION,
            ErrorCode.TOOL_EXECUTION_FAILED: ErrorCategory.TOOL_EXECUTION,
            ErrorCode.TOOL_TIMEOUT: ErrorCategory.TOOL_EXECUTION,
            ErrorCode.TOOL_VALIDATION_FAILED: ErrorCategory.TOOL_EXECUTION,
            ErrorCode.ORCHESTRATOR_STATE_ERROR: ErrorCategory.ORCHESTRATOR,
            ErrorCode.WORKFLOW_STEP_FAILED: ErrorCategory.ORCHESTRATOR,
            ErrorCode.SESSION_MANAGEMENT_ERROR: ErrorCategory.ORCHESTRATOR,
            ErrorCode.FILE_NOT_FOUND: ErrorCategory.FILE_OPERATION,
            ErrorCode.FILE_PERMISSION_DENIED: ErrorCategory.FILE_OPERATION,
            ErrorCode.FILE_CORRUPTED: ErrorCategory.FILE_OPERATION,
            ErrorCode.DISK_SPACE_FULL: ErrorCategory.FILE_OPERATION,
            ErrorCode.SYSTEM_RESOURCE_EXHAUSTED: ErrorCategory.SYSTEM,
            ErrorCode.CONFIGURATION_ERROR: ErrorCategory.SYSTEM,
            ErrorCode.INTERNAL_ERROR: ErrorCategory.SYSTEM
        }
    
    def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> SclipError:
        """Handle and classify an error"""
        
        # Convert to SclipError if needed
        if isinstance(error, SclipError):
            sclip_error = error
        else:
            sclip_error = self._classify_error(error, context)
        
        # Log the error
        self._log_error(sclip_error, context, session_id, user_id)
        
        # Track error statistics
        self._track_error(sclip_error)
        
        # Add context-specific suggestions
        self._add_context_suggestions(sclip_error, context)
        
        return sclip_error
    
    def _classify_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> SclipError:
        """Classify and convert a generic exception to SclipError"""
        
        error_message = str(error)
        error_type = type(error).__name__
        
        # Determine error code and category based on error type and message
        if "validation" in error_message.lower() or "invalid" in error_message.lower():
            error_code = ErrorCode.INVALID_INPUT
            category = ErrorCategory.VALIDATION
            severity = ErrorSeverity.LOW
            recoverable = True
            suggested_actions = ["Check input format", "Verify required fields"]
            
        elif "not found" in error_message.lower() or "missing" in error_message.lower():
            error_code = ErrorCode.RESOURCE_NOT_FOUND
            category = ErrorCategory.RESOURCE_NOT_FOUND
            severity = ErrorSeverity.MEDIUM
            recoverable = True
            suggested_actions = ["Verify resource exists", "Check resource path"]
            
        elif "timeout" in error_message.lower():
            error_code = ErrorCode.NETWORK_TIMEOUT
            category = ErrorCategory.NETWORK
            severity = ErrorSeverity.MEDIUM
            recoverable = True
            suggested_actions = ["Retry operation", "Check network connection"]
            
        elif "permission" in error_message.lower() or "access denied" in error_message.lower():
            error_code = ErrorCode.FILE_PERMISSION_DENIED
            category = ErrorCategory.FILE_OPERATION
            severity = ErrorSeverity.HIGH
            recoverable = True
            suggested_actions = ["Check file permissions", "Run as administrator"]
            
        elif "database" in error_message.lower() or "sql" in error_message.lower():
            error_code = ErrorCode.DATABASE_QUERY_FAILED
            category = ErrorCategory.DATABASE
            severity = ErrorSeverity.HIGH
            recoverable = True
            suggested_actions = ["Check database connection", "Verify database schema"]
            
        elif "tool" in error_message.lower():
            error_code = ErrorCode.TOOL_EXECUTION_FAILED
            category = ErrorCategory.TOOL_EXECUTION
            severity = ErrorSeverity.MEDIUM
            recoverable = True
            suggested_actions = ["Check tool configuration", "Verify tool dependencies"]
            
        else:
            error_code = ErrorCode.INTERNAL_ERROR
            category = ErrorCategory.SYSTEM
            severity = ErrorSeverity.CRITICAL
            recoverable = False
            suggested_actions = ["Contact support", "Check system logs"]
        
        return SclipError(
            message=error_message,
            error_code=error_code,
            category=category,
            severity=severity,
            details={
                "error_type": error_type,
                "context": context or {},
                "traceback": traceback.format_exc()
            },
            recoverable=recoverable,
            suggested_actions=suggested_actions
        )
    
    def _log_error(
        self,
        error: SclipError,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """Log error with appropriate level"""
        
        log_data = {
            "error_code": error.error_code.value,
            "category": error.category.value,
            "severity": error.severity.value,
            "message": error.message,
            "recoverable": error.recoverable,
            "session_id": session_id,
            "user_id": user_id,
            "context": context or {}
        }
        
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical("Critical error occurred", **log_data)
        elif error.severity == ErrorSeverity.HIGH:
            logger.error("High severity error occurred", **log_data)
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning("Medium severity error occurred", **log_data)
        else:
            logger.info("Low severity error occurred", **log_data)
    
    def _track_error(self, error: SclipError):
        """Track error statistics"""
        
        error_key = f"{error.error_code.value}_{error.category.value}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Add to history
        self.error_history.append({
            "timestamp": error.timestamp.isoformat(),
            "error_code": error.error_code.value,
            "category": error.category.value,
            "severity": error.severity.value,
            "message": error.message,
            "recoverable": error.recoverable
        })
        
        # Trim history if too large
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size:]
    
    def _add_context_suggestions(self, error: SclipError, context: Optional[Dict[str, Any]] = None):
        """Add context-specific recovery suggestions"""
        
        if not context:
            return
        
        # Add context-specific suggestions based on error type
        if error.category == ErrorCategory.TOOL_EXECUTION:
            if "script_writer" in str(context):
                error.suggested_actions.append("Check script template files")
            elif "broll_finder" in str(context):
                error.suggested_actions.append("Verify B-roll source availability")
            elif "voiceover_generator" in str(context):
                error.suggested_actions.append("Check TTS service configuration")
        
        elif error.category == ErrorCategory.FILE_OPERATION:
            if "temp" in str(context):
                error.suggested_actions.append("Clear temporary files")
            elif "output" in str(context):
                error.suggested_actions.append("Check output directory permissions")
        
        elif error.category == ErrorCategory.DATABASE:
            if "preferences" in str(context):
                error.suggested_actions.append("Reset user preferences")
            elif "session" in str(context):
                error.suggested_actions.append("Restart session")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics"""
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_counts": self.error_counts,
            "recent_errors": self.error_history[-10:],  # Last 10 errors
            "error_categories": {
                category.value: sum(
                    count for key, count in self.error_counts.items() 
                    if category.value in key
                )
                for category in ErrorCategory
            }
        }
    
    def get_recovery_suggestions(self, error_code: ErrorCode) -> List[str]:
        """Get recovery suggestions for a specific error code"""
        
        suggestions_map = {
            ErrorCode.INVALID_INPUT: [
                "Check input format and required fields",
                "Verify data types match expected format"
            ],
            ErrorCode.RESOURCE_NOT_FOUND: [
                "Verify the resource exists and is accessible",
                "Check file paths and permissions"
            ],
            ErrorCode.NETWORK_TIMEOUT: [
                "Retry the operation",
                "Check network connectivity",
                "Verify external service availability"
            ],
            ErrorCode.TOOL_EXECUTION_FAILED: [
                "Check tool configuration",
                "Verify tool dependencies are installed",
                "Check tool input parameters"
            ],
            ErrorCode.DATABASE_QUERY_FAILED: [
                "Check database connection",
                "Verify database schema",
                "Check for database locks or conflicts"
            ],
            ErrorCode.FILE_PERMISSION_DENIED: [
                "Check file and directory permissions",
                "Run application with appropriate privileges",
                "Verify file ownership"
            ]
        }
        
        return suggestions_map.get(error_code, ["Contact support for assistance"])
    
    def clear_error_history(self):
        """Clear error history"""
        self.error_history.clear()
        self.error_counts.clear()
        logger.info("Error history cleared")

# Global error handler instance
error_handler = ErrorHandler() 