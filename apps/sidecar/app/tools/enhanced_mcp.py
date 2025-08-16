"""
Enhanced MCP (Model Context Protocol) Implementation for Sclip
Provides dynamic tool discovery, RAG integration, and intelligent tool orchestration
"""

import asyncio
import json
import inspect
from typing import Dict, Any, List, Optional, Callable, Type
from dataclasses import dataclass, asdict, field
from enum import Enum
import uuid
from datetime import datetime
from pathlib import Path

from ..utils.logger import get_logger
from ..services.rag_service import rag_service, Document, SearchResult

logger = get_logger(__name__)

class MCPMessageType(Enum):
    """Enhanced MCP message types"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"
    TOOL_DISCOVERY = "tool_discovery"
    CONTEXT_UPDATE = "context_update"

class MCPToolCall(Enum):
    """Enhanced MCP tool call types"""
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    TOOL_ERROR = "tool_error"
    TOOL_DISCOVERY = "tool_discovery"
    CONTEXT_QUERY = "context_query"

@dataclass
class MCPToolSchema:
    """Enhanced MCP tool schema definition"""
    name: str
    description: str
    inputSchema: Dict[str, Any]
    outputSchema: Dict[str, Any]
    examples: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    category: str = "general"
    version: str = "1.0.0"
    author: str = "sclip"
    dependencies: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)

@dataclass
class MCPMessage:
    """Enhanced MCP message structure"""
    id: str
    type: MCPMessageType
    method: str
    params: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

@dataclass
class ToolExecution:
    """Represents a tool execution"""
    tool_name: str
    input_params: Dict[str, Any]
    output_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

class EnhancedMCPProtocol:
    """
    Enhanced MCP Protocol implementation for Sclip
    Provides dynamic tool discovery, RAG integration, and intelligent orchestration
    """
    
    def __init__(self):
        self.tools: Dict[str, MCPToolSchema] = {}
        self.tool_instances: Dict[str, Any] = {}
        self.message_history: List[MCPMessage] = []
        self.execution_history: List[ToolExecution] = []
        self.session_id: Optional[str] = None
        self.rag_service = rag_service
        
        logger.info("Enhanced MCP Protocol initialized")
    
    def register_tool(self, tool_instance: Any, schema: Optional[MCPToolSchema] = None) -> None:
        """Register a tool with enhanced schema"""
        try:
            # Extract tool information from instance
            tool_name = getattr(tool_instance, 'name', tool_instance.__class__.__name__)
            tool_description = getattr(tool_instance, 'description', 'No description available')
            
            # Create schema if not provided
            if schema is None:
                schema = MCPToolSchema(
                    name=tool_name,
                    description=tool_description,
                    inputSchema=self._extract_input_schema(tool_instance),
                    outputSchema=self._extract_output_schema(tool_instance),
                    examples=self._extract_examples(tool_instance),
                    tags=self._extract_tags(tool_instance),
                    category=self._extract_category(tool_instance),
                    capabilities=self._extract_capabilities(tool_instance)
                )
            
            # Register tool
            self.tools[tool_name] = schema
            self.tool_instances[tool_name] = tool_instance
            
            logger.info(f"Registered enhanced MCP tool: {tool_name}")
            
        except Exception as e:
            logger.error(f"Error registering tool {tool_name}: {e}")
    
    def _extract_input_schema(self, tool_instance: Any) -> Dict[str, Any]:
        """Extract input schema from tool instance"""
        try:
            if hasattr(tool_instance, 'get_input_schema'):
                return tool_instance.get_input_schema()
            elif hasattr(tool_instance, 'input_schema'):
                return tool_instance.input_schema
            else:
                # Try to infer from method signature
                if hasattr(tool_instance, 'run'):
                    sig = inspect.signature(tool_instance.run)
                    schema = {}
                    for param_name, param in sig.parameters.items():
                        if param_name != 'self':
                            schema[param_name] = {
                                "type": "any",
                                "description": f"Parameter {param_name}",
                                "required": param.default == inspect.Parameter.empty
                            }
                    return schema
                return {}
        except Exception as e:
            logger.error(f"Error extracting input schema: {e}")
            return {}
    
    def _extract_output_schema(self, tool_instance: Any) -> Dict[str, Any]:
        """Extract output schema from tool instance"""
        try:
            if hasattr(tool_instance, 'get_output_schema'):
                return tool_instance.get_output_schema()
            elif hasattr(tool_instance, 'output_schema'):
                return tool_instance.output_schema
            else:
                return {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "result": {"type": "object"},
                        "error": {"type": "string"}
                    }
                }
        except Exception as e:
            logger.error(f"Error extracting output schema: {e}")
            return {}
    
    def _extract_examples(self, tool_instance: Any) -> List[Dict[str, Any]]:
        """Extract examples from tool instance"""
        try:
            if hasattr(tool_instance, 'examples'):
                return tool_instance.examples
            elif hasattr(tool_instance, 'get_examples'):
                return tool_instance.get_examples()
            else:
                return []
        except Exception:
            return []
    
    def _extract_tags(self, tool_instance: Any) -> List[str]:
        """Extract tags from tool instance"""
        try:
            if hasattr(tool_instance, 'tags'):
                return tool_instance.tags
            else:
                # Infer tags from class name and description
                tags = []
                class_name = tool_instance.__class__.__name__.lower()
                if 'script' in class_name:
                    tags.append('script')
                if 'video' in class_name:
                    tags.append('video')
                if 'media' in class_name:
                    tags.append('media')
                if 'voice' in class_name:
                    tags.append('voice')
                return tags
        except Exception:
            return []
    
    def _extract_category(self, tool_instance: Any) -> str:
        """Extract category from tool instance"""
        try:
            if hasattr(tool_instance, 'category'):
                return tool_instance.category
            else:
                # Infer category from class name
                class_name = tool_instance.__class__.__name__.lower()
                if 'script' in class_name:
                    return 'content_creation'
                elif 'video' in class_name:
                    return 'video_processing'
                elif 'media' in class_name:
                    return 'media_management'
                else:
                    return 'general'
        except Exception:
            return 'general'
    
    def _extract_capabilities(self, tool_instance: Any) -> List[str]:
        """Extract capabilities from tool instance"""
        try:
            if hasattr(tool_instance, 'capabilities'):
                return tool_instance.capabilities
            else:
                # Infer capabilities from methods
                capabilities = []
                methods = [method for method in dir(tool_instance) if not method.startswith('_')]
                
                if 'run' in methods:
                    capabilities.append('execute')
                if 'validate' in methods:
                    capabilities.append('validate')
                if 'get_schema' in methods:
                    capabilities.append('schema')
                
                return capabilities
        except Exception:
            return ['execute']
    
    async def discover_tools(self, query: str = None) -> List[MCPToolSchema]:
        """Discover relevant tools based on query or context"""
        try:
            if query:
                # Use RAG to find relevant tools
                relevant_tools = await self.rag_service.get_relevant_tools(query)
                discovered_tools = []
                
                for tool_info in relevant_tools:
                    tool_name = tool_info['name']
                    if tool_name in self.tools:
                        discovered_tools.append(self.tools[tool_name])
                
                # Also search by tags and categories
                query_lower = query.lower()
                for tool_name, schema in self.tools.items():
                    if (query_lower in schema.description.lower() or
                        any(tag.lower() in query_lower for tag in schema.tags) or
                        schema.category.lower() in query_lower):
                        if schema not in discovered_tools:
                            discovered_tools.append(schema)
                
                return discovered_tools
            else:
                # Return all tools
                return list(self.tools.values())
                
        except Exception as e:
            logger.error(f"Error discovering tools: {e}")
            return []
    
    async def execute_tool(self, tool_name: str, params: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a tool with enhanced context and logging"""
        try:
            if tool_name not in self.tool_instances:
                raise Exception(f"Tool {tool_name} not found")
            
            tool_instance = self.tool_instances[tool_name]
            start_time = asyncio.get_event_loop().time()
            
            # Log execution start
            execution = ToolExecution(
                tool_name=tool_name,
                input_params=params,
                timestamp=datetime.now().isoformat()
            )
            
            # Execute tool
            if asyncio.iscoroutinefunction(tool_instance.run):
                result = await tool_instance.run(params)
            else:
                result = tool_instance.run(params)
            
            # Calculate execution time
            execution_time = asyncio.get_event_loop().time() - start_time
            execution.execution_time = execution_time
            execution.output_result = result
            
            # Add to execution history
            self.execution_history.append(execution)
            
            # Add to RAG for future context
            await self.rag_service.add_tool_result(tool_name, result, {
                "session_id": self.session_id,
                "execution_time": execution_time,
                "input_params": params
            })
            
            logger.info(f"Executed tool {tool_name} in {execution_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            
            # Log error
            execution = ToolExecution(
                tool_name=tool_name,
                input_params=params,
                error=str(e),
                timestamp=datetime.now().isoformat()
            )
            self.execution_history.append(execution)
            
            raise
    
    async def get_context_for_query(self, query: str) -> str:
        """Get relevant context for a query using RAG"""
        try:
            # Get RAG context
            rag_context = await self.rag_service.get_context_for_query(query)
            
            # Get relevant tools
            relevant_tools = await self.discover_tools(query)
            tools_context = ""
            if relevant_tools:
                tools_context = "**Relevant Tools:**\n"
                for tool in relevant_tools[:3]:  # Top 3 tools
                    tools_context += f"- {tool.name}: {tool.description}\n"
            
            # Get recent executions
            recent_executions = ""
            if self.execution_history:
                recent_executions = "**Recent Tool Executions:**\n"
                for execution in self.execution_history[-3:]:  # Last 3 executions
                    status = "✅" if execution.error is None else "❌"
                    recent_executions += f"- {status} {execution.tool_name}: {execution.execution_time:.2f}s\n"
            
            # Combine context
            full_context = f"{rag_context}\n\n{tools_context}\n\n{recent_executions}"
            return full_context.strip()
            
        except Exception as e:
            logger.error(f"Error getting context for query: {e}")
            return ""
    
    def create_tool_call_message(self, tool_name: str, params: Dict[str, Any], context: Dict[str, Any] = None) -> MCPMessage:
        """Create an enhanced tool call message"""
        return MCPMessage(
            id=str(uuid.uuid4()),
            type=MCPMessageType.REQUEST,
            method=MCPToolCall.TOOL_CALL.value,
            params={
                "tool": tool_name,
                "arguments": params,
                "context": context or {}
            },
            timestamp=datetime.now().isoformat()
        )
    
    def create_tool_result_message(self, request_id: str, result: Dict[str, Any], execution_time: float = 0.0) -> MCPMessage:
        """Create an enhanced tool result message"""
        return MCPMessage(
            id=str(uuid.uuid4()),
            type=MCPMessageType.RESPONSE,
            method=MCPToolCall.TOOL_RESULT.value,
            params={"request_id": request_id},
            result={
                **result,
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat()
            },
            timestamp=datetime.now().isoformat()
        )
    
    def create_tool_discovery_message(self, tools: List[MCPToolSchema]) -> MCPMessage:
        """Create a tool discovery message"""
        return MCPMessage(
            id=str(uuid.uuid4()),
            type=MCPMessageType.TOOL_DISCOVERY,
            method=MCPToolCall.TOOL_DISCOVERY.value,
            params={"tools": [asdict(tool) for tool in tools]},
            timestamp=datetime.now().isoformat()
        )
    
    async def process_llm_response(self, response: str, context: Dict[str, Any] = None) -> List[MCPMessage]:
        """Process LLM response and extract tool calls"""
        try:
            messages = []
            
            # Try to parse JSON tool calls
            tool_calls = self._extract_json_tool_calls(response)
            
            for tool_call in tool_calls:
                tool_name = tool_call.get("tool")
                params = tool_call.get("args", {})
                
                if tool_name and tool_name in self.tools:
                    # Create tool call message
                    message = self.create_tool_call_message(tool_name, params, context)
                    messages.append(message)
                    
                    # Execute tool
                    try:
                        result = await self.execute_tool(tool_name, params, context)
                        result_message = self.create_tool_result_message(
                            message.id, result
                        )
                        messages.append(result_message)
                    except Exception as e:
                        error_message = MCPMessage(
                            id=str(uuid.uuid4()),
                            type=MCPMessageType.ERROR,
                            method=MCPToolCall.TOOL_ERROR.value,
                            params={"request_id": message.id},
                            error={"message": str(e)},
                            timestamp=datetime.now().isoformat()
                        )
                        messages.append(error_message)
            
            return messages
            
        except Exception as e:
            logger.error(f"Error processing LLM response: {e}")
            return []
    
    def _extract_json_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """Extract JSON tool calls from response"""
        tool_calls = []
        
        # Look for JSON blocks
        import re
        json_pattern = r'```json\s*(\{.*?\})\s*```'
        matches = re.findall(json_pattern, response, re.DOTALL)
        
        for match in matches:
            try:
                json_data = json.loads(match)
                
                # Check for tool_calls array
                if "tool_calls" in json_data:
                    tool_calls.extend(json_data["tool_calls"])
                
                # Check for single tool_call
                elif "tool_call" in json_data:
                    tool_calls.append(json_data["tool_call"])
                
                # Check for action format
                elif "action" in json_data:
                    tool_calls.append(json_data)
                
            except json.JSONDecodeError:
                continue
        
        return tool_calls
    
    def format_tools_for_llm(self) -> str:
        """Format tools for LLM consumption with enhanced information"""
        try:
            tools_info = []
            
            for tool_name, schema in self.tools.items():
                tool_info = {
                    "name": tool_name,
                    "description": schema.description,
                    "category": schema.category,
                    "tags": schema.tags,
                    "capabilities": schema.capabilities,
                    "input_schema": schema.inputSchema,
                    "output_schema": schema.outputSchema,
                    "examples": schema.examples
                }
                tools_info.append(tool_info)
            
            return json.dumps(tools_info, indent=2)
            
        except Exception as e:
            logger.error(f"Error formatting tools for LLM: {e}")
            return "[]"
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get enhanced MCP statistics"""
        try:
            stats = {
                "total_tools": len(self.tools),
                "total_executions": len(self.execution_history),
                "total_messages": len(self.message_history),
                "session_id": self.session_id,
                "tools_by_category": {},
                "recent_executions": []
            }
            
            # Tools by category
            for tool_name, schema in self.tools.items():
                category = schema.category
                if category not in stats["tools_by_category"]:
                    stats["tools_by_category"][category] = []
                stats["tools_by_category"][category].append(tool_name)
            
            # Recent executions
            for execution in self.execution_history[-5:]:
                stats["recent_executions"].append({
                    "tool": execution.tool_name,
                    "timestamp": execution.timestamp,
                    "execution_time": execution.execution_time,
                    "success": execution.error is None
                })
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting MCP statistics: {e}")
            return {"error": str(e)}

# Global enhanced MCP instance
enhanced_mcp = EnhancedMCPProtocol() 