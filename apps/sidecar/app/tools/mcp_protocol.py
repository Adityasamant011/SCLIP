"""
Model Context Protocol (MCP) Implementation for Sclip
Provides standardized tool communication for agentic workflows
"""
import json
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

from ..utils.logger import get_logger

logger = get_logger(__name__)

class MCPMessageType(Enum):
    """MCP message types"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"

class MCPToolCall(Enum):
    """MCP tool call types"""
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    TOOL_ERROR = "tool_error"

@dataclass
class MCPMessage:
    """Standard MCP message structure"""
    id: str
    type: MCPMessageType
    method: str
    params: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None

@dataclass
class MCPToolSchema:
    """MCP tool schema definition"""
    name: str
    description: str
    inputSchema: Dict[str, Any]
    outputSchema: Dict[str, Any]
    examples: List[Dict[str, Any]]

class MCPProtocol:
    """
    Model Context Protocol implementation for Sclip
    Provides standardized communication between LLM and tools
    """
    
    def __init__(self):
        self.tools: Dict[str, MCPToolSchema] = {}
        self.message_history: List[MCPMessage] = []
        self.session_id: Optional[str] = None
        
        logger.info("MCP Protocol initialized")
    
    def register_tool(self, schema: MCPToolSchema) -> None:
        """Register a tool with MCP schema"""
        self.tools[schema.name] = schema
        logger.info(f"Registered MCP tool: {schema.name}")
    
    def create_tool_call_message(self, tool_name: str, params: Dict[str, Any]) -> MCPMessage:
        """Create a tool call message"""
        return MCPMessage(
            id=str(uuid.uuid4()),
            type=MCPMessageType.REQUEST,
            method=MCPToolCall.TOOL_CALL.value,
            params={
                "tool": tool_name,
                "arguments": params
            },
            timestamp=asyncio.get_event_loop().time()
        )
    
    def create_tool_result_message(self, request_id: str, result: Dict[str, Any]) -> MCPMessage:
        """Create a tool result message"""
        return MCPMessage(
            id=str(uuid.uuid4()),
            type=MCPMessageType.RESPONSE,
            method=MCPToolCall.TOOL_RESULT.value,
            params={"request_id": request_id},
            result=result,
            timestamp=asyncio.get_event_loop().time()
        )
    
    def create_tool_error_message(self, request_id: str, error: str) -> MCPMessage:
        """Create a tool error message"""
        return MCPMessage(
            id=str(uuid.uuid4()),
            type=MCPMessageType.ERROR,
            method=MCPToolCall.TOOL_ERROR.value,
            params={"request_id": request_id},
            error={"message": error},
            timestamp=asyncio.get_event_loop().time()
        )
    
    def parse_llm_response(self, response: str) -> Optional[MCPMessage]:
        """Parse LLM response for MCP tool calls"""
        try:
            # Try to parse as JSON
            data = json.loads(response)
            
            # Check if it's a tool call
            if isinstance(data, dict) and "tool_calls" in data:
                tool_call = data["tool_calls"][0]  # Assume first tool call
                return MCPMessage(
                    id=str(uuid.uuid4()),
                    type=MCPMessageType.REQUEST,
                    method=MCPToolCall.TOOL_CALL.value,
                    params={
                        "tool": tool_call.get("tool"),
                        "arguments": tool_call.get("args", {})
                    }
                )
            
            return None
            
        except json.JSONDecodeError:
            # Not JSON, check for tool call patterns
            if "ACTION:" in response and "PARAMETERS:" in response:
                # Parse structured text response
                return self._parse_structured_response(response)
            
            return None
    
    def _parse_structured_response(self, response: str) -> Optional[MCPMessage]:
        """Parse structured text response for tool calls"""
        try:
            lines = response.split('\n')
            tool_name = None
            params = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith("ACTION:"):
                    tool_name = line.split(":", 1)[1].strip()
                elif line.startswith("PARAMETERS:"):
                    # Parse parameters
                    param_text = line.split(":", 1)[1].strip()
                    if param_text.startswith("{") and param_text.endswith("}"):
                        params = json.loads(param_text)
            
            if tool_name:
                return MCPMessage(
                    id=str(uuid.uuid4()),
                    type=MCPMessageType.REQUEST,
                    method=MCPToolCall.TOOL_CALL.value,
                    params={
                        "tool": tool_name,
                        "arguments": params
                    }
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to parse structured response: {e}")
            return None
    
    def get_tools_list(self) -> List[Dict[str, Any]]:
        """Get list of available tools for LLM"""
        return [
            {
                "name": schema.name,
                "description": schema.description,
                "inputSchema": schema.inputSchema,
                "outputSchema": schema.outputSchema,
                "examples": schema.examples
            }
            for schema in self.tools.values()
        ]
    
    def validate_tool_call(self, message: MCPMessage) -> bool:
        """Validate tool call message"""
        if message.method != MCPToolCall.TOOL_CALL.value:
            return False
        
        tool_name = message.params.get("tool")
        if not tool_name or tool_name not in self.tools:
            return False
        
        # Validate parameters against schema
        schema = self.tools[tool_name]
        arguments = message.params.get("arguments", {})
        
        return self._validate_arguments(arguments, schema.inputSchema)
    
    def _validate_arguments(self, arguments: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Validate arguments against schema"""
        for field_name, field_info in schema.items():
            if field_info.get("required", True):
                if field_name not in arguments:
                    return False
                
                # Type validation
                expected_type = field_info.get("type", "string")
                actual_value = arguments[field_name]
                
                if expected_type == "string" and not isinstance(actual_value, str):
                    return False
                elif expected_type == "integer" and not isinstance(actual_value, int):
                    return False
                elif expected_type == "boolean" and not isinstance(actual_value, bool):
                    return False
        
        return True
    
    def format_tools_for_llm(self) -> str:
        """Format tools for LLM prompt"""
        tools_text = []
        
        for schema in self.tools.values():
            tool_text = f"## {schema.name}\n"
            tool_text += f"**Description:** {schema.description}\n"
            
            # Input schema
            tool_text += "**Input Parameters:**\n"
            for param_name, param_info in schema.inputSchema.items():
                required = "required" if param_info.get("required", True) else "optional"
                tool_text += f"- `{param_name}` ({param_info.get('type', 'string')}, {required}): {param_info.get('description', 'No description')}\n"
            
            # Output schema
            tool_text += "**Output:**\n"
            for output_name, output_info in schema.outputSchema.items():
                tool_text += f"- `{output_name}` ({output_info.get('type', 'string')}): {output_info.get('description', 'No description')}\n"
            
            # Examples
            if schema.examples:
                tool_text += "**Examples:**\n"
                for i, example in enumerate(schema.examples[:2]):
                    tool_text += f"Example {i+1}:\n"
                    tool_text += f"Input: {json.dumps(example.get('input', {}), indent=2)}\n"
                    tool_text += f"Output: {json.dumps(example.get('output', {}), indent=2)}\n"
            
            tools_text.append(tool_text)
        
        return "\n\n".join(tools_text)
    
    def log_message(self, message: MCPMessage) -> None:
        """Log MCP message for debugging"""
        self.message_history.append(message)
        
        # Keep only last 100 messages
        if len(self.message_history) > 100:
            self.message_history = self.message_history[-100:]
        
        logger.debug(f"MCP Message: {message.method} - {message.params.get('tool', 'unknown')}")

# Global MCP instance
mcp_protocol = MCPProtocol() 