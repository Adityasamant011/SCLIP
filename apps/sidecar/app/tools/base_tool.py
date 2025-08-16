"""
Base Tool Class for Sclip
Provides a standard interface for all deterministic tools
"""
import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, ValidationError
from enum import Enum

from ..utils.logger import get_logger

logger = get_logger(__name__)

class ToolStatus(Enum):
    """Tool execution status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

class ToolError(Exception):
    """Custom exception for tool errors"""
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

class ToolInputSchema(BaseModel):
    """Base input schema for tools"""
    pass

class ToolOutputSchema(BaseModel):
    """Base output schema for tools"""
    success: bool = Field(description="Whether the tool execution was successful")
    output: Optional[Dict[str, Any]] = Field(default=None, description="Tool output data")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    execution_time: float = Field(description="Execution time in seconds")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

class BaseTool(ABC):
    """
    Abstract base class for all Sclip tools
    Provides standard interface and validation for deterministic tool execution
    """
    
    def __init__(self, name: str, description: str, version: str = "1.0.0"):
        self.name = name
        self.description = description
        self.version = version
        self.status = ToolStatus.PENDING
        self.execution_start_time: Optional[float] = None
        self.execution_end_time: Optional[float] = None
        self.last_error: Optional[str] = None
        self.execution_count = 0
        self.success_count = 0
        self.total_execution_time = 0.0
        
        logger.info(f"Tool initialized: {self.name} v{self.version}")
    
    @abstractmethod
    def get_input_schema(self) -> Dict[str, Any]:
        """Get the input schema for this tool"""
        pass
    
    @abstractmethod
    def get_output_schema(self) -> Dict[str, Any]:
        """Get the output schema for this tool"""
        pass
    
    @abstractmethod
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given input data"""
        pass
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data against the tool's schema"""
        try:
            # Create a dynamic Pydantic model from the schema
            schema = self.get_input_schema()
            if not schema:
                return True  # No schema means no validation needed
            
            # Create a temporary model for validation
            fields = {}
            for field_name, field_info in schema.items():
                field_type = field_info.get("type", "string")
                required = field_info.get("required", True)
                
                if field_type == "string":
                    fields[field_name] = (str, ...) if required else (Optional[str], None)
                elif field_type == "integer":
                    fields[field_name] = (int, ...) if required else (Optional[int], None)
                elif field_type == "float":
                    fields[field_name] = (float, ...) if required else (Optional[float], None)
                elif field_type == "boolean":
                    fields[field_name] = (bool, ...) if required else (Optional[bool], None)
                elif field_type == "array":
                    fields[field_name] = (List[Any], ...) if required else (Optional[List[Any]], None)
                elif field_type == "object":
                    fields[field_name] = (Dict[str, Any], ...) if required else (Optional[Dict[str, Any]], None)
                else:
                    fields[field_name] = (Any, ...) if required else (Optional[Any], None)
            
            # Create and validate the model with proper annotations
            model_dict = {}
            for field_name, (field_type, default) in fields.items():
                if default is None:
                    model_dict[field_name] = (field_type, None)
                else:
                    model_dict[field_name] = (field_type, default)
            
            # Create the model class with proper type annotations
            InputModel = type("InputModel", (BaseModel,), {
                "__annotations__": {k: v[0] for k, v in model_dict.items()},
                **{k: v[1] for k, v in model_dict.items()}
            })
            
            InputModel(**input_data)
            return True
            
        except ValidationError as e:
            logger.error(f"Input validation failed for {self.name}: {e}")
            self.last_error = f"Input validation failed: {e}"
            return False
        except Exception as e:
            logger.error(f"Unexpected error during input validation for {self.name}: {e}")
            self.last_error = f"Validation error: {e}"
            return False
    
    def validate_output(self, output_data: Dict[str, Any]) -> bool:
        """Validate output data against the tool's schema"""
        try:
            # Create a dynamic Pydantic model from the schema
            schema = self.get_output_schema()
            if not schema:
                return True  # No schema means no validation needed
            
            # Create a temporary model for validation
            fields = {}
            for field_name, field_info in schema.items():
                field_type = field_info.get("type", "string")
                required = field_info.get("required", True)
                
                if field_type == "string":
                    fields[field_name] = (str, ...) if required else (Optional[str], None)
                elif field_type == "integer":
                    fields[field_name] = (int, ...) if required else (Optional[int], None)
                elif field_type == "float":
                    fields[field_name] = (float, ...) if required else (Optional[float], None)
                elif field_type == "boolean":
                    fields[field_name] = (bool, ...) if required else (Optional[bool], None)
                elif field_type == "array":
                    fields[field_name] = (List[Any], ...) if required else (Optional[List[Any]], None)
                elif field_type == "object":
                    fields[field_name] = (Dict[str, Any], ...) if required else (Optional[Dict[str, Any]], None)
                else:
                    fields[field_name] = (Any, ...) if required else (Optional[Any], None)
            
            # Create and validate the model with proper annotations
            model_dict = {}
            for field_name, (field_type, default) in fields.items():
                if default is None:
                    model_dict[field_name] = (field_type, None)
                else:
                    model_dict[field_name] = (field_type, default)
            
            # Create the model class with proper type annotations
            OutputModel = type("OutputModel", (BaseModel,), {
                "__annotations__": {k: v[0] for k, v in model_dict.items()},
                **{k: v[1] for k, v in model_dict.items()}
            })
            
            OutputModel(**output_data)
            return True
            
        except ValidationError as e:
            logger.error(f"Output validation failed for {self.name}: {e}")
            self.last_error = f"Output validation failed: {e}"
            return False
        except Exception as e:
            logger.error(f"Unexpected error during output validation for {self.name}: {e}")
            self.last_error = f"Validation error: {e}"
            return False
    
    def get_schema(self) -> Dict[str, Any]:
        """Get complete tool schema including metadata"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "input_schema": self.get_input_schema(),
            "output_schema": self.get_output_schema(),
            "metadata": {
                "execution_count": self.execution_count,
                "success_count": self.success_count,
                "success_rate": self.success_count / max(self.execution_count, 1),
                "average_execution_time": self.total_execution_time / max(self.execution_count, 1),
                "last_error": self.last_error
            }
        }
    
    async def execute(self, input_data: Dict[str, Any], timeout: float = 300.0) -> Dict[str, Any]:
        """
        Execute the tool with validation, timeout handling, and error management
        """
        self.execution_count += 1
        self.status = ToolStatus.RUNNING
        self.execution_start_time = time.time()
        
        try:
            logger.info(f"Executing tool {self.name} with input: {input_data}")
            
            # Validate input
            if not self.validate_input(input_data):
                raise ToolError(f"Input validation failed for {self.name}", "VALIDATION_ERROR")
            
            # Execute with timeout
            try:
                result = await asyncio.wait_for(self.run(input_data), timeout=timeout)
            except asyncio.TimeoutError:
                self.status = ToolStatus.TIMEOUT
                raise ToolError(f"Tool {self.name} execution timed out after {timeout} seconds", "TIMEOUT_ERROR")
            
            # Validate output
            if not self.validate_output(result):
                raise ToolError(f"Output validation failed for {self.name}", "VALIDATION_ERROR")
            
            # Update statistics
            self.execution_end_time = time.time()
            execution_time = self.execution_end_time - self.execution_start_time
            self.total_execution_time += execution_time
            self.success_count += 1
            self.status = ToolStatus.SUCCESS
            self.last_error = None
            
            # Add execution metadata
            result["execution_time"] = execution_time
            result["tool_name"] = self.name
            result["tool_version"] = self.version
            
            logger.info(f"Tool {self.name} executed successfully in {execution_time:.2f}s")
            return result
            
        except ToolError:
            # Re-raise tool errors
            self.status = ToolStatus.FAILED
            self.execution_end_time = time.time()
            raise
            
        except Exception as e:
            # Handle unexpected errors
            self.status = ToolStatus.FAILED
            self.execution_end_time = time.time()
            self.last_error = str(e)
            
            logger.error(f"Unexpected error in tool {self.name}: {e}")
            raise ToolError(f"Unexpected error in {self.name}: {e}", "EXECUTION_ERROR")
    
    def cancel(self):
        """Cancel the tool execution"""
        if self.status == ToolStatus.RUNNING:
            self.status = ToolStatus.CANCELLED
            logger.info(f"Tool {self.name} execution cancelled")
    
    def reset(self):
        """Reset tool state"""
        self.status = ToolStatus.PENDING
        self.execution_start_time = None
        self.execution_end_time = None
        self.last_error = None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current tool status"""
        return {
            "name": self.name,
            "status": self.status.value,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "success_rate": self.success_count / max(self.execution_count, 1),
            "average_execution_time": self.total_execution_time / max(self.execution_count, 1),
            "last_error": self.last_error,
            "current_execution_time": (
                time.time() - self.execution_start_time 
                if self.execution_start_time and self.status == ToolStatus.RUNNING 
                else None
            )
        } 