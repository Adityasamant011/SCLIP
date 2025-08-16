"""
Enhanced Tool Registry with MCP-like Protocol Support
Provides tool discovery, schema validation, and execution for agentic workflows
"""
import asyncio
import json
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from .base_tool import BaseTool
from ..utils.logger import get_logger

logger = get_logger(__name__)

class ToolCategory(Enum):
    """Tool categories for organization"""
    SCRIPT_GENERATION = "script_generation"
    MEDIA_COLLECTION = "media_collection"
    VIDEO_PROCESSING = "video_processing"
    AUDIO_PROCESSING = "audio_processing"
    PROJECT_MANAGEMENT = "project_management"
    ANALYSIS = "analysis"
    UTILITY = "utility"

@dataclass
class ToolSchema:
    """Enhanced tool schema with MCP-like structure"""
    name: str
    description: str
    category: ToolCategory
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    examples: List[Dict[str, Any]]
    version: str = "1.0.0"
    async_support: bool = True
    streaming_support: bool = False

class EnhancedToolRegistry:
    """
    Enhanced tool registry with MCP-like protocol support
    Provides tool discovery, validation, and execution for agentic workflows
    """
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self.schemas: Dict[str, ToolSchema] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Enhanced Tool Registry initialized")
    
    def register_tool(self, tool: BaseTool, schema: ToolSchema) -> None:
        """Register a tool with its enhanced schema"""
            self.tools[tool.name] = tool
        self.schemas[tool.name] = schema
        self.performance_metrics[tool.name] = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "average_execution_time": 0.0,
            "last_used": None
        }
        
        logger.info(f"Registered tool: {tool.name} (v{schema.version})")
    
    def get_tool_schema(self, tool_name: str) -> Optional[ToolSchema]:
        """Get tool schema for LLM prompt generation"""
        return self.schemas.get(tool_name)
    
    def get_all_schemas(self) -> Dict[str, ToolSchema]:
        """Get all tool schemas for LLM context"""
        return self.schemas.copy()
    
    def get_tools_by_category(self, category: ToolCategory) -> List[str]:
        """Get tools by category"""
        return [name for name, schema in self.schemas.items() 
                if schema.category == category]
    
    async def execute_tool(self, tool_name: str, input_data: Dict[str, Any], 
                          session_id: str = None) -> Dict[str, Any]:
        """Execute a tool with enhanced error handling and metrics"""
        
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        tool = self.tools[tool_name]
        schema = self.schemas[tool_name]
        
        # Update metrics
        self.performance_metrics[tool_name]["total_calls"] += 1
        self.performance_metrics[tool_name]["last_used"] = asyncio.get_event_loop().time()
        
        # Validate input against schema
        try:
            self._validate_input(input_data, schema.input_schema)
        except Exception as e:
            self.performance_metrics[tool_name]["failed_calls"] += 1
            raise ValueError(f"Input validation failed for {tool_name}: {e}")
        
        # Execute tool
        start_time = asyncio.get_event_loop().time()
        try:
            result = await tool.run(input_data)
            
            # Validate output against schema
            self._validate_output(result, schema.output_schema)
            
            # Update metrics
            execution_time = asyncio.get_event_loop().time() - start_time
            self.performance_metrics[tool_name]["successful_calls"] += 1
            self._update_average_execution_time(tool_name, execution_time)
            
            # Log execution
            self.execution_history.append({
                "tool_name": tool_name,
                "session_id": session_id,
                "input_data": input_data,
                "result": result,
                "execution_time": execution_time,
                "timestamp": asyncio.get_event_loop().time(),
                "status": "success"
            })
            
            logger.info(f"Tool {tool_name} executed successfully in {execution_time:.2f}s")
            return result
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            self.performance_metrics[tool_name]["failed_calls"] += 1
            
            # Log failed execution
            self.execution_history.append({
                "tool_name": tool_name,
                "session_id": session_id,
                "input_data": input_data,
                "error": str(e),
                "execution_time": execution_time,
                "timestamp": asyncio.get_event_loop().time(),
                "status": "failed"
            })
            
            logger.error(f"Tool {tool_name} failed after {execution_time:.2f}s: {e}")
            raise
    
    def _validate_input(self, input_data: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Validate input data against schema"""
        # Basic validation - could be enhanced with JSON Schema
        for field_name, field_info in schema.items():
            if field_info.get("required", True):
                if field_name not in input_data:
                    raise ValueError(f"Required field '{field_name}' missing")
                
                # Type validation
                expected_type = field_info.get("type", "string")
                actual_value = input_data[field_name]
                
                if expected_type == "string" and not isinstance(actual_value, str):
                    raise ValueError(f"Field '{field_name}' must be string, got {type(actual_value)}")
                elif expected_type == "integer" and not isinstance(actual_value, int):
                    raise ValueError(f"Field '{field_name}' must be integer, got {type(actual_value)}")
                elif expected_type == "boolean" and not isinstance(actual_value, bool):
                    raise ValueError(f"Field '{field_name}' must be boolean, got {type(actual_value)}")
    
    def _validate_output(self, output_data: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Validate output data against schema"""
        # Basic validation - could be enhanced
        if not isinstance(output_data, dict):
            raise ValueError("Tool output must be a dictionary")
        
        # Check for required success field
        if "success" not in output_data:
            raise ValueError("Tool output must include 'success' field")
    
    def _update_average_execution_time(self, tool_name: str, execution_time: float) -> None:
        """Update average execution time for a tool"""
        metrics = self.performance_metrics[tool_name]
        current_avg = metrics["average_execution_time"]
        total_successful = metrics["successful_calls"]
        
        # Calculate new average
        new_avg = ((current_avg * (total_successful - 1)) + execution_time) / total_successful
        metrics["average_execution_time"] = new_avg
    
    def get_tool_descriptions_for_llm(self) -> str:
        """Generate tool descriptions for LLM prompts"""
        descriptions = []
        
        for tool_name, schema in self.schemas.items():
            desc = f"## {tool_name}\n"
            desc += f"**Description:** {schema.description}\n"
            desc += f"**Category:** {schema.category.value}\n"
            desc += f"**Version:** {schema.version}\n"
            
            # Input schema
            desc += "**Input Parameters:**\n"
            for param_name, param_info in schema.input_schema.items():
                required = "required" if param_info.get("required", True) else "optional"
                desc += f"- `{param_name}` ({param_info.get('type', 'string')}, {required}): {param_info.get('description', 'No description')}\n"
            
            # Output schema
            desc += "**Output:**\n"
            for output_name, output_info in schema.output_schema.items():
                desc += f"- `{output_name}` ({output_info.get('type', 'string')}): {output_info.get('description', 'No description')}\n"
            
            # Examples
            if schema.examples:
                desc += "**Examples:**\n"
                for i, example in enumerate(schema.examples[:2]):  # Show first 2 examples
                    desc += f"Example {i+1}:\n"
                    desc += f"Input: {json.dumps(example.get('input', {}), indent=2)}\n"
                    desc += f"Output: {json.dumps(example.get('output', {}), indent=2)}\n"
            
            descriptions.append(desc)
        
        return "\n\n".join(descriptions)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for monitoring"""
        return {
            "total_tools": len(self.tools),
            "total_executions": sum(m["total_calls"] for m in self.performance_metrics.values()),
            "success_rate": sum(m["successful_calls"] for m in self.performance_metrics.values()) / 
                          max(sum(m["total_calls"] for m in self.performance_metrics.values()), 1),
            "tool_metrics": self.performance_metrics,
            "recent_executions": self.execution_history[-10:]  # Last 10 executions
        }

# Global registry instance
tool_registry = EnhancedToolRegistry() 