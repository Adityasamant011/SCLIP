"""
True AI Agent for Sclip
Integrates RAG, MCP, and intelligent orchestration for context-aware decision making
"""

import asyncio
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import uuid

from ..utils.logger import get_logger
from ..services.rag_service import rag_service, Document, SearchResult
from ..tools.enhanced_mcp import enhanced_mcp, MCPMessage, MCPToolSchema, ToolExecution
from ..core.context_manager import context_manager

logger = get_logger(__name__)

class AgentState(Enum):
    """AI Agent states"""
    IDLE = "idle"
    THINKING = "thinking"
    PLANNING = "planning"
    EXECUTING = "executing"
    OBSERVING = "observing"
    DECIDING = "deciding"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class AgentAction:
    """Represents an action the agent can take"""
    id: str
    action_type: str
    description: str
    parameters: Dict[str, Any]
    priority: int = 1
    dependencies: List[str] = field(default_factory=list)
    estimated_duration: float = 0.0
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class AgentContext:
    """Enhanced agent context with RAG and MCP integration"""
    session_id: str
    user_message: str
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    current_project: Dict[str, Any] = field(default_factory=dict)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    tool_executions: List[ToolExecution] = field(default_factory=list)
    rag_context: str = ""
    discovered_tools: List[MCPToolSchema] = field(default_factory=list)
    agent_state: AgentState = AgentState.IDLE
    iteration_count: int = 0
    max_iterations: int = 10

@dataclass
class AgentResponse:
    """Enhanced agent response with RAG and MCP integration"""
    message: str
    actions: List[AgentAction] = field(default_factory=list)
    context_updates: Dict[str, Any] = field(default_factory=dict)
    rag_context: str = ""
    discovered_tools: List[MCPToolSchema] = field(default_factory=list)
    reasoning: str = ""
    confidence: float = 0.0
    next_suggestions: List[str] = field(default_factory=list)

class TrueAIAgent:
    """
    True AI Agent with RAG and MCP integration
    Provides intelligent, context-aware decision making and tool orchestration
    """
    
    def __init__(self, ai_service, websocket_manager):
        self.ai_service = ai_service
        self.websocket_manager = websocket_manager
        self.rag_service = rag_service
        self.mcp = enhanced_mcp
        self.context_manager = context_manager
        
        # Agent state
        self.current_session_id: Optional[str] = None
        self.agent_context: Optional[AgentContext] = None
        self.execution_history: List[AgentAction] = []
        
        logger.info("True AI Agent initialized with RAG and MCP integration")
    
    async def process_message(self, session_id: str, user_message: str) -> AgentResponse:
        """Process user message with true AI agentic capabilities"""
        try:
            # Initialize agent context
            self.current_session_id = session_id
            self.agent_context = await self._build_agent_context(session_id, user_message)
            
            # Start the true agentic loop
            return await self._execute_agentic_loop()
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return AgentResponse(
                message=f"Sorry, I encountered an error: {str(e)}",
                reasoning=f"Error in agent processing: {str(e)}",
                confidence=0.0
            )
    
    async def _build_agent_context(self, session_id: str, user_message: str) -> AgentContext:
        """Build comprehensive agent context with RAG and MCP integration"""
        try:
            # Get conversation history
            conversation_history = self.context_manager._get_conversation_history(session_id)
            
            # Get current project state
            project_state = self.context_manager._build_project_state(session_id)
            
            # Get user preferences
            user_preferences = self.context_manager.sessions.get(session_id, {}).get("user_preferences", {})
            
            # Get RAG context for the query
            rag_context = await self.rag_service.get_context_for_query(user_message)
            
            # Discover relevant tools
            discovered_tools = await self.mcp.discover_tools(user_message)
            
            # Build agent context
            context = AgentContext(
                session_id=session_id,
                user_message=user_message,
                conversation_history=conversation_history,
                current_project=project_state,
                user_preferences=user_preferences,
                rag_context=rag_context,
                discovered_tools=discovered_tools
            )
            
            # Add conversation to RAG
            await self.rag_service.add_conversation_context(session_id, conversation_history)
            
            logger.info(f"Built agent context for session {session_id}")
            return context
            
        except Exception as e:
            logger.error(f"Error building agent context: {e}")
            raise
    
    async def _execute_agentic_loop(self) -> AgentResponse:
        """Execute the true agentic loop with RAG and MCP integration"""
        try:
            self.agent_context.agent_state = AgentState.THINKING
            
            # Reduce max iterations to prevent infinite loops
            max_iterations = 3  # Reduced from 10
            
            while self.agent_context.iteration_count < max_iterations:
                self.agent_context.iteration_count += 1
                
                logger.info(f"🤔 AGENTIC LOOP ITERATION {self.agent_context.iteration_count}")
                
                # STEP 1: THINK - Analyze current state and plan
                await self._send_agent_state_update("thinking", f"Analyzing request and context (iteration {self.agent_context.iteration_count})")
                
                planning_result = await self._think_and_plan()
                
                # Check if we have actions to execute
                if not planning_result.actions:
                    # No actions needed - this could be conversational, informational, or completed
                    logger.info("✅ AGENTIC LOOP COMPLETE: No actions needed")
                    return await self._create_final_response(planning_result.message)
                
                # STEP 2: EXECUTE - Run planned actions
                await self._send_agent_state_update("executing", f"Executing {len(planning_result.actions)} actions")
                
                executed_actions = await self._execute_actions(planning_result.actions)
                
                # STEP 3: OBSERVE - Analyze results and update context
                await self._send_agent_state_update("observing", "Analyzing execution results")
                
                await self._observe_and_update_context(executed_actions)
                
                # STEP 4: DECIDE - Check if task is complete
                completion_check = await self._check_task_completion(executed_actions)
                
                if completion_check.get("completed", False):
                    logger.info("✅ AGENTIC LOOP COMPLETE: Task completed successfully")
                    return await self._create_final_response(
                        completion_check.get("final_message", "Task completed successfully!"),
                        executed_actions
                    )
                
                # Check if we've reached max iterations
                if self.agent_context.iteration_count >= max_iterations:
                    logger.info(f"🔄 AGENTIC LOOP COMPLETE: Max iterations ({max_iterations}) reached")
                    return await self._create_final_response(
                        "I've completed the main tasks. Let me know if you need anything else!",
                        executed_actions
                    )
                
                # Continue to next iteration
                logger.info(f"🔄 AGENTIC LOOP ITERATION {self.agent_context.iteration_count} COMPLETE")
            
            # Max iterations reached
            return await self._create_final_response(
                "I've completed the main tasks. Let me know if you need anything else!",
                []
            )
            
        except Exception as e:
            logger.error(f"Error in agentic loop: {e}")
            self.agent_context.agent_state = AgentState.ERROR
            raise
    
    async def _think_and_plan(self) -> AgentResponse:
        """Enhanced thinking and planning with intelligent workflow analysis"""
        try:
            # Build comprehensive thinking prompt
            thinking_prompt = await self._build_thinking_prompt()
            
            # Get AI response with enhanced reasoning
            ai_response = await self.ai_service.generate_response(thinking_prompt)
            
            # Extract reasoning and user message
            reasoning = self._extract_reasoning_from_response(ai_response)
            user_message = self._extract_user_message_from_response(ai_response)
            
            # Parse actions with enhanced intelligence
            actions = await self._parse_actions_from_response(ai_response)
            
            # If no actions found, try to infer from context
            if not actions:
                actions = await self._infer_actions_from_request()
            
            # Enhance actions with context-aware parameters
            enhanced_actions = await self._enhance_actions_with_context(actions)
            
            # Generate next suggestions
            next_suggestions = await self._generate_next_suggestions()
            
            # Create enhanced response
            response = AgentResponse(
                message=user_message,
                actions=enhanced_actions,
                reasoning=reasoning,
                context_updates={
                    "iteration": self.agent_context.iteration_count,
                    "actions_planned": len(enhanced_actions),
                    "reasoning": reasoning
                },
                next_suggestions=next_suggestions
            )
            
            logger.info(f"Planned {len(enhanced_actions)} actions with reasoning: {reasoning[:100]}...")
            return response
            
        except Exception as e:
            logger.error(f"Error in thinking and planning: {e}")
            return AgentResponse(
                message="I'm having trouble planning right now. Let me try a simpler approach.",
                actions=[],
                reasoning="Error occurred during planning phase"
            )
    
    async def _enhance_actions_with_context(self, actions: List[AgentAction]) -> List[AgentAction]:
        """Enhance actions with context-aware parameters and preferences"""
        try:
            enhanced_actions = []
            
            for action in actions:
                # Get user preferences for this action type
                preferences = self._get_preferences_for_action(action.action_type)
                
                # Enhance parameters with user preferences
                enhanced_params = action.parameters.copy()
                
                if "script" in action.action_type.lower():
                    # Apply script preferences
                    if "preferred_script_style" in preferences and "style" not in enhanced_params:
                        enhanced_params["style"] = preferences["preferred_script_style"]
                    if "preferred_script_length" in preferences and "length" not in enhanced_params:
                        enhanced_params["length"] = preferences["preferred_script_length"]
                
                elif "broll" in action.action_type.lower() or "media" in action.action_type.lower():
                    # Apply media preferences
                    if "preferred_media_style" in preferences and "style" not in enhanced_params:
                        enhanced_params["style"] = preferences["preferred_media_style"]
                    if "preferred_media_count" in preferences and "count" not in enhanced_params:
                        enhanced_params["count"] = preferences["preferred_media_count"]
                
                elif "voiceover" in action.action_type.lower():
                    # Apply voiceover preferences
                    if "preferred_voiceover_voice" in preferences and "voice" not in enhanced_params:
                        enhanced_params["voice"] = preferences["preferred_voiceover_voice"]
                
                # Create enhanced action
                enhanced_action = AgentAction(
                    id=action.id,
                    action_type=action.action_type,
                    description=action.description,
                    parameters=enhanced_params,
                    priority=action.priority,
                    dependencies=action.dependencies,
                    estimated_duration=action.estimated_duration,
                    status=action.status,
                    result=action.result,
                    error=action.error,
                    timestamp=action.timestamp
                )
                
                enhanced_actions.append(enhanced_action)
            
            return enhanced_actions
            
        except Exception as e:
            logger.error(f"Error enhancing actions: {e}")
            return actions
    
    def _get_preferences_for_action(self, action_type: str) -> Dict[str, Any]:
        """Get user preferences relevant to the action type"""
        try:
            preferences = {}
            
            if "script" in action_type.lower():
                preferences.update({
                    "preferred_script_style": self.agent_context.user_preferences.get("preferred_script_style", "cinematic"),
                    "preferred_script_length": self.agent_context.user_preferences.get("preferred_script_length", "60 seconds")
                })
            
            elif "broll" in action_type.lower() or "media" in action_type.lower():
                preferences.update({
                    "preferred_media_style": self.agent_context.user_preferences.get("preferred_media_style", "cinematic"),
                    "preferred_media_count": self.agent_context.user_preferences.get("preferred_media_count", 8)
                })
            
            elif "voiceover" in action_type.lower():
                preferences.update({
                    "preferred_voiceover_voice": self.agent_context.user_preferences.get("preferred_voiceover_voice", "en-US-Neural2-A")
                })
            
            return preferences
            
        except Exception as e:
            logger.error(f"Error getting preferences: {e}")
            return {}
    
    async def _build_thinking_prompt(self) -> str:
        """Build comprehensive thinking prompt with RAG and MCP context"""
        try:
            # Get RAG context
            rag_context = self.agent_context.rag_context
            
            # Get discovered tools
            tools_info = self.mcp.format_tools_for_llm()
            
            # Get conversation history
            conversation_text = self._format_conversation_history()
            
            # Get project state
            project_state = self._format_project_state()
            
            # Get recent tool executions
            recent_executions = self._format_recent_executions()
            
            prompt = f"""
You are Sclip, a TRUE AI AGENT with RAG (Retrieval Augmented Generation) and MCP (Model Context Protocol) capabilities.

**🎯 YOUR CAPABILITIES:**
- RAG: You have access to semantic search and context retrieval
- MCP: You can discover and execute tools dynamically
- Context Awareness: You remember everything and build on previous interactions
- Intelligent Planning: You can plan multi-step workflows
- Adaptive Learning: You learn from each interaction
- Natural Conversation: You can engage in general conversation and answer questions

**📊 CURRENT CONTEXT:**
- Session ID: {self.agent_context.session_id}
- Iteration: {self.agent_context.iteration_count}
- User Message: {self.agent_context.user_message}

**🧠 RAG CONTEXT (Semantic Search Results):**
{rag_context if rag_context else "No relevant context found"}

**🛠️ AVAILABLE TOOLS:**
{tools_info}

**💬 CONVERSATION HISTORY:**
{conversation_text}

**📁 PROJECT STATE:**
{project_state}

**⚙️ RECENT EXECUTIONS:**
{recent_executions}

**🤔 THINKING PROCESS:**
1. **Analyze the user's request** - What do they want to accomplish?
2. **Check RAG context** - What relevant information do we have?
3. **Determine response type** - Is this a conversation, question, or task?
4. **Discover relevant tools** - What tools can help accomplish this?
5. **Plan the workflow** - What steps are needed?
6. **Adapt to context** - How does this fit with what we've done before?

**🎯 RESPONSE TYPES:**

**1. CONVERSATIONAL RESPONSES** (No tools needed):
- Greetings: "hi", "hello", "hey", "good morning"
- General questions: "who is messi?", "what's the weather?", "tell me about..."
- Casual conversation: "how are you?", "thanks", "that's cool"
- Questions about capabilities: "what can you do?", "help"

**2. TOOL-BASED RESPONSES** (Use tools):
- Video creation: "make me a script", "create a video", "find B-roll"
- Content generation: "write a script about...", "generate voiceover"
- Media processing: "process this video", "add effects"
- File operations: "download media", "organize files"

**3. INFORMATIONAL RESPONSES** (Use RAG + knowledge):
- Factual questions: "who is messi?", "what are the romans?"
- Explanations: "how does...", "what is...", "explain..."
- Research: "find information about...", "search for..."

**📝 RESPONSE FORMAT:**

**For CONVERSATIONAL/INFORMATIONAL responses:**
```json
{{
    "response_type": "conversational",
    "reasoning": "User asked a general question about Messi, so I'll provide an informative response",
    "user_message": "Lionel Messi is an Argentine professional footballer widely regarded as one of the greatest players of all time. He's known for his incredible dribbling skills, goal-scoring ability, and numerous records including 7 Ballon d'Or awards. He currently plays for Inter Miami in the MLS and has had legendary careers with Barcelona and the Argentine national team.",
    "tool_calls": [],
    "context_updates": {{"last_topic": "Lionel Messi"}}
}}
```

**For TOOL-BASED responses:**
```json
{{
    "response_type": "workflow",
    "reasoning": "User requested a script about The Romans, so I'll use the script_writer tool",
    "tool_calls": [
        {{
            "tool": "script_writer",
            "args": {{
                "topic": "The Romans",
                "style": "cinematic",
                "length": "60 seconds"
            }},
            "description": "Creating a cinematic script about The Romans"
        }}
    ],
    "user_message": "I'll create a cinematic script about The Romans for you!"
}}
```

**🎯 BE INTELLIGENT AND FLEXIBLE:**
- **Always respond naturally** - Don't be rigid or robotic
- **Use RAG context** - Leverage available information
- **Choose the right response type** - Conversational, informational, or tool-based
- **Be helpful and engaging** - Provide value in every interaction
- **Adapt to the user's needs** - Whether they want conversation, information, or tasks
- **Don't force tools** - Only use tools when they're actually needed

**🚀 EXAMPLES:**

User: "hi" → Conversational response
User: "who is messi?" → Informational response with facts
User: "make me a script about the romans" → Tool-based response
User: "what can you do?" → Conversational response about capabilities
User: "thanks" → Conversational response
User: "create a video about space" → Tool-based response with multiple tools
"""
            
            return prompt
            
        except Exception as e:
            logger.error(f"Error building thinking prompt: {e}")
            raise
    
    async def _parse_actions_from_response(self, response: str) -> List[AgentAction]:
        """Parse actions from AI response"""
        try:
            actions = []
            
            # Check if this is a conversational response (no tools needed)
            if "response_type" in response and "conversational" in response:
                logger.info("📝 Detected conversational response - no tools needed")
                return []
            
            # Check if this is an informational response (no tools needed)
            if "response_type" in response and "informational" in response:
                logger.info("📚 Detected informational response - no tools needed")
                return []
            
            # Try to extract JSON tool calls
            tool_calls = self._extract_json_tool_calls(response)
            
            for i, tool_call in enumerate(tool_calls):
                action = AgentAction(
                    id=str(uuid.uuid4()),
                    action_type=tool_call.get("tool", ""),
                    description=tool_call.get("description", ""),
                    parameters=tool_call.get("args", {}),
                    priority=i + 1
                )
                actions.append(action)
            
            return actions
            
        except Exception as e:
            logger.error(f"Error parsing actions: {e}")
            return []
    
    def _extract_reasoning_from_response(self, response: str) -> str:
        """Extract reasoning from AI response"""
        try:
            # Look for reasoning in JSON
            if "reasoning" in response:
                match = re.search(r'"reasoning":\s*"([^"]+)"', response)
                if match:
                    return match.group(1)
            
            # Look for reasoning in markdown
            if "**reasoning:**" in response.lower():
                lines = response.split('\n')
                for i, line in enumerate(lines):
                    if "reasoning:" in line.lower():
                        return line.split(':', 1)[1].strip()
            
            return "AI analyzed the request and determined the best course of action."
            
        except Exception as e:
            logger.error(f"Error extracting reasoning: {e}")
            return "AI reasoning not available"

    def _extract_user_message_from_response(self, response: str) -> str:
        """Extract user-friendly message from AI response"""
        try:
            # First, try to extract JSON response
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                try:
                    json_data = json.loads(json_match.group(1))
                    if "user_message" in json_data:
                        return json_data["user_message"]
                except json.JSONDecodeError:
                    pass
            
            # Check for conversational responses
            if "response_type" in response and "conversational" in response:
                # Extract the actual message content
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
                if json_match:
                    try:
                        json_data = json.loads(json_match.group(1))
                        if "user_message" in json_data:
                            return json_data["user_message"]
                    except:
                        pass
            
            # If no user_message found, try to extract from the response
            # Remove JSON blocks and return the clean text
            clean_response = response
            json_pattern = r'```json\s*\{.*?\}\s*```'
            clean_response = re.sub(json_pattern, '', clean_response, flags=re.DOTALL)
            clean_response = clean_response.strip()
            
            # If we have clean text, return it
            if clean_response and len(clean_response) > 10:
                return clean_response
            
            # Fallback for conversational responses
            if any(word in self.agent_context.user_message.lower() for word in ["hi", "hello", "hey", "who", "what", "how", "why", "when", "where"]):
                return "Hello! I'm here to help you with video creation, general questions, or just conversation. What would you like to know or create?"
            
            # Fallback
            return "I'm processing your request..."
            
        except Exception as e:
            logger.error(f"Error extracting user message: {e}")
            return "I'm here to help you with video creation and general questions. What would you like to do?"
    
    async def _execute_actions(self, actions: List[AgentAction]) -> List[AgentAction]:
        """Execute a list of actions with enhanced error handling and recovery"""
        try:
            executed_actions = []
            
            for action in actions:
                try:
                    logger.info(f"🚀 Executing action: {action.action_type} with params: {action.parameters}")
                    
                    # Send action start message
                    await self._send_action_start(action)
                    
                    # Execute action via MCP with retry logic
                    result = await self._execute_action_with_retry(action)
                    
                    logger.info(f"✅ Action {action.action_type} completed successfully: {result}")
                    
                    # Update action with result
                    action.result = result
                    action.status = "completed"
                    executed_actions.append(action)
                    
                    # Send action complete message
                    await self._send_action_complete(action)
                    
                    # Send GUI updates for this tool
                    await self._send_gui_updates_for_tool(action.action_type, result)
                    
                except Exception as e:
                    logger.error(f"❌ Error executing action {action.action_type}: {e}")
                    action.error = str(e)
                    action.status = "failed"
                    executed_actions.append(action)
                    
                    # Send action error message
                    await self._send_action_error(action)
                    
                    # Try to recover from the error
                    await self._handle_action_failure(action, e)
            
            return executed_actions
            
        except Exception as e:
            logger.error(f"Error executing actions: {e}")
            raise
    
    async def _execute_action_with_retry(self, action: AgentAction, max_retries: int = 3) -> Dict[str, Any]:
        """Execute action with intelligent retry logic"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Execute action via MCP
                result = await self.mcp.execute_tool(
                    action.action_type,
                    action.parameters,
                    {"session_id": self.agent_context.session_id}
                )
                
                # Validate result
                if result and isinstance(result, dict):
                    return result
                else:
                    raise Exception("Invalid result format")
                    
            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed for {action.action_type}: {e}")
                
                if attempt < max_retries - 1:
                    # Wait before retry with exponential backoff
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    
                    # Try to adjust parameters for retry
                    action.parameters = await self._adjust_parameters_for_retry(action, e)
        
        # All retries failed
        raise last_error
    
    async def _adjust_parameters_for_retry(self, action: AgentAction, error: Exception) -> Dict[str, Any]:
        """Intelligently adjust parameters for retry based on error"""
        try:
            adjusted_params = action.parameters.copy()
            
            # Adjust based on error type
            error_str = str(error).lower()
            
            if "rate limit" in error_str or "429" in error_str:
                # Rate limit error - reduce count or add delay
                if "count" in adjusted_params:
                    adjusted_params["count"] = max(1, adjusted_params["count"] // 2)
            
            elif "invalid" in error_str or "parameter" in error_str:
                # Parameter error - use defaults
                if "script" in action.action_type.lower():
                    adjusted_params.setdefault("style", "cinematic")
                    adjusted_params.setdefault("length", "60 seconds")
                elif "broll" in action.action_type.lower():
                    adjusted_params.setdefault("count", 5)
                    adjusted_params.setdefault("style", "cinematic")
                elif "voiceover" in action.action_type.lower():
                    adjusted_params.setdefault("voice", "en-US-Neural2-A")
            
            elif "timeout" in error_str:
                # Timeout error - reduce complexity
                if "length" in adjusted_params:
                    adjusted_params["length"] = "30 seconds"
                if "count" in adjusted_params:
                    adjusted_params["count"] = max(1, adjusted_params["count"] // 2)
            
            return adjusted_params
            
        except Exception as e:
            logger.error(f"Error adjusting parameters: {e}")
            return action.parameters
    
    async def _handle_action_failure(self, action: AgentAction, error: Exception) -> None:
        """Handle action failure with intelligent recovery"""
        try:
            # Log the failure for learning
            if "failure_patterns" not in self.agent_context.user_preferences:
                self.agent_context.user_preferences["failure_patterns"] = []
            
            failure_pattern = {
                "action_type": action.action_type,
                "parameters": action.parameters,
                "error": str(error),
                "timestamp": action.timestamp
            }
            self.agent_context.user_preferences["failure_patterns"].append(failure_pattern)
            
            # Try to suggest alternative actions
            alternative_actions = await self._suggest_alternative_actions(action, error)
            
            if alternative_actions:
                logger.info(f"Suggested {len(alternative_actions)} alternative actions for failed {action.action_type}")
                
                # Send alternative suggestions to user
                await self.websocket_manager.send_message(self.agent_context.session_id, {
                    "type": "alternative_suggestions",
                    "failed_action": action.action_type,
                    "alternatives": alternative_actions,
                    "timestamp": datetime.now().isoformat()
                })
            
        except Exception as e:
            logger.error(f"Error handling action failure: {e}")
    
    async def _suggest_alternative_actions(self, failed_action: AgentAction, error: Exception) -> List[str]:
        """Suggest alternative actions when one fails"""
        try:
            alternatives = []
            error_str = str(error).lower()
            
            if "script" in failed_action.action_type.lower():
                alternatives.extend([
                    "Try creating a script with different parameters",
                    "Use a simpler script style",
                    "Create a shorter script"
                ])
            
            elif "broll" in failed_action.action_type.lower():
                alternatives.extend([
                    "Try searching for different media",
                    "Reduce the number of media files",
                    "Use different search terms"
                ])
            
            elif "voiceover" in failed_action.action_type.lower():
                alternatives.extend([
                    "Try a different voice",
                    "Use a shorter script",
                    "Generate voiceover with different settings"
                ])
            
            elif "video" in failed_action.action_type.lower():
                alternatives.extend([
                    "Try processing with different settings",
                    "Use fewer effects",
                    "Process a shorter video"
                ])
            
            return alternatives[:2]  # Limit to 2 alternatives
            
        except Exception as e:
            logger.error(f"Error suggesting alternatives: {e}")
            return []

    async def _send_gui_updates_for_tool(self, tool_name: str, result: Dict[str, Any]):
        """Send GUI updates based on tool execution result"""
        try:
            if tool_name == "script_writer" and result.get("script_text"):
                await self.websocket_manager.send_message(self.agent_context.session_id, {
                    "type": "gui_update",
                    "update_type": "script_created",
                    "data": {
                        "script_content": result["script_text"]
                    },
                    "timestamp": datetime.now().isoformat()
                })
                logger.info(f"📝 GUI update sent for script_writer: {len(result['script_text'])} characters")
            
            elif tool_name == "broll_finder" and result.get("downloaded_files"):
                await self.websocket_manager.send_message(self.agent_context.session_id, {
                    "type": "gui_update",
                    "update_type": "media_downloaded",
                    "data": {
                        "media_files": result["downloaded_files"]
                    },
                    "timestamp": datetime.now().isoformat()
                })
                logger.info(f"🖼️ GUI update sent for broll_finder: {len(result['downloaded_files'])} files")
            
            elif tool_name == "voiceover_generator" and result.get("audio_path"):
                await self.websocket_manager.send_message(self.agent_context.session_id, {
                    "type": "gui_update",
                    "update_type": "voiceover_created",
                    "data": {
                        "audio_path": result["audio_path"]
                    },
                    "timestamp": datetime.now().isoformat()
                })
                logger.info(f"🎤 GUI update sent for voiceover_generator: {result['audio_path']}")
            
            elif tool_name == "video_processor" and result.get("video_path"):
                await self.websocket_manager.send_message(self.agent_context.session_id, {
                    "type": "gui_update",
                    "update_type": "video_created",
                    "data": {
                        "video_path": result["video_path"],
                        "thumbnail": result.get("thumbnail")
                    },
                    "timestamp": datetime.now().isoformat()
                })
                logger.info(f"🎬 GUI update sent for video_processor: {result['video_path']}")
        
        except Exception as e:
            logger.error(f"Error sending GUI updates for tool {tool_name}: {e}")
    
    async def _observe_and_update_context(self, executed_actions: List[AgentAction]) -> None:
        """Enhanced context observation and update with intelligent learning"""
        try:
            # Update conversation history with executed actions
            for action in executed_actions:
                if action.status == "completed":
                    # Add successful action to context
                    self.agent_context.tool_executions.append(
                        ToolExecution(
                            tool_name=action.action_type,
                            parameters=action.parameters,
                            result=action.result,
                            timestamp=action.timestamp
                        )
                    )
                    
                    # Learn from successful actions
                    await self._learn_from_action(action)
                    
                    # Update project state based on action
                    await self._update_project_state_from_action(action)
                    
                elif action.status == "failed":
                    # Learn from failures
                    await self._learn_from_failure(action)
            
            # Update RAG context with new information
            if executed_actions:
                await self._update_rag_context(executed_actions)
            
            # Update user preferences based on patterns
            await self._update_user_preferences(executed_actions)
            
            logger.info(f"Updated context with {len(executed_actions)} actions")
            
        except Exception as e:
            logger.error(f"Error updating context: {e}")
    
    async def _learn_from_action(self, action: AgentAction) -> None:
        """Learn from successful actions to improve future decisions"""
        try:
            # Extract patterns from successful actions
            if "script" in action.action_type.lower():
                # Learn script preferences
                if action.result and "style" in action.parameters:
                    self.agent_context.user_preferences["script_style"] = action.parameters["style"]
                if action.result and "length" in action.parameters:
                    self.agent_context.user_preferences["script_length"] = action.parameters["length"]
            
            elif "broll" in action.action_type.lower() or "media" in action.action_type.lower():
                # Learn media preferences
                if action.result and "style" in action.parameters:
                    self.agent_context.user_preferences["media_style"] = action.parameters["style"]
                if action.result and "count" in action.parameters:
                    self.agent_context.user_preferences["media_count"] = action.parameters["count"]
            
            elif "voiceover" in action.action_type.lower():
                # Learn voiceover preferences
                if action.result and "voice" in action.parameters:
                    self.agent_context.user_preferences["voiceover_voice"] = action.parameters["voice"]
            
            # Store successful patterns
            if "successful_patterns" not in self.agent_context.user_preferences:
                self.agent_context.user_preferences["successful_patterns"] = []
            
            pattern = {
                "action_type": action.action_type,
                "parameters": action.parameters,
                "timestamp": action.timestamp
            }
            self.agent_context.user_preferences["successful_patterns"].append(pattern)
            
        except Exception as e:
            logger.error(f"Error learning from action: {e}")
    
    async def _learn_from_failure(self, action: AgentAction) -> None:
        """Learn from failed actions to avoid future mistakes"""
        try:
            # Store failure patterns
            if "failure_patterns" not in self.agent_context.user_preferences:
                self.agent_context.user_preferences["failure_patterns"] = []
            
            failure_pattern = {
                "action_type": action.action_type,
                "parameters": action.parameters,
                "error": action.error,
                "timestamp": action.timestamp
            }
            self.agent_context.user_preferences["failure_patterns"].append(failure_pattern)
            
        except Exception as e:
            logger.error(f"Error learning from failure: {e}")
    
    async def _update_project_state_from_action(self, action: AgentAction) -> None:
        """Update project state based on executed action"""
        try:
            if "script" in action.action_type.lower() and action.result:
                # Update script in project state
                if "scripts" not in self.agent_context.current_project:
                    self.agent_context.current_project["scripts"] = []
                
                script_data = {
                    "content": action.result.get("script_text", ""),
                    "topic": action.parameters.get("topic", ""),
                    "style": action.parameters.get("style", ""),
                    "timestamp": action.timestamp
                }
                self.agent_context.current_project["scripts"].append(script_data)
            
            elif "broll" in action.action_type.lower() or "media" in action.action_type.lower():
                # Update media in project state
                if "media_files" not in self.agent_context.current_project:
                    self.agent_context.current_project["media_files"] = []
                
                if action.result and "files" in action.result:
                    for file_info in action.result["files"]:
                        media_data = {
                            "filename": file_info.get("filename", ""),
                            "path": file_info.get("path", ""),
                            "type": file_info.get("type", "image"),
                            "timestamp": action.timestamp
                        }
                        self.agent_context.current_project["media_files"].append(media_data)
            
            elif "voiceover" in action.action_type.lower():
                # Update voiceover in project state
                if "voiceovers" not in self.agent_context.current_project:
                    self.agent_context.current_project["voiceovers"] = []
                
                voiceover_data = {
                    "file": action.result.get("voiceover_file", ""),
                    "script": action.result.get("script_used", ""),
                    "voice": action.parameters.get("voice", ""),
                    "timestamp": action.timestamp
                }
                self.agent_context.current_project["voiceovers"].append(voiceover_data)
            
            elif "video" in action.action_type.lower() or "processor" in action.action_type.lower():
                # Update video in project state
                if "videos" not in self.agent_context.current_project:
                    self.agent_context.current_project["videos"] = []
                
                video_data = {
                    "file": action.result.get("video_file", ""),
                    "duration": action.result.get("duration", ""),
                    "components": action.result.get("components", []),
                    "timestamp": action.timestamp
                }
                self.agent_context.current_project["videos"].append(video_data)
            
        except Exception as e:
            logger.error(f"Error updating project state: {e}")
    
    async def _update_rag_context(self, executed_actions: List[AgentAction]) -> None:
        """Update RAG context with new information from executed actions"""
        try:
            for action in executed_actions:
                if action.status == "completed" and action.result:
                    # Add action result to RAG
                    content = f"Action: {action.action_type}\nParameters: {json.dumps(action.parameters)}\nResult: {json.dumps(action.result)}"
                    
                    await self.rag_service.add_document(
                        content=content,
                        metadata={
                            "action_type": action.action_type,
                            "session_id": self.agent_context.session_id,
                            "timestamp": action.timestamp,
                            "status": "completed"
                        }
                    )
            
        except Exception as e:
            logger.error(f"Error updating RAG context: {e}")
    
    async def _update_user_preferences(self, executed_actions: List[AgentAction]) -> None:
        """Update user preferences based on action patterns"""
        try:
            # Analyze patterns in executed actions
            script_actions = [a for a in executed_actions if "script" in a.action_type.lower()]
            media_actions = [a for a in executed_actions if "broll" in a.action_type.lower() or "media" in a.action_type.lower()]
            voiceover_actions = [a for a in executed_actions if "voiceover" in a.action_type.lower()]
            
            # Update preferences based on patterns
            if script_actions:
                latest_script = script_actions[-1]
                if latest_script.status == "completed":
                    self.agent_context.user_preferences["preferred_script_style"] = latest_script.parameters.get("style", "cinematic")
                    self.agent_context.user_preferences["preferred_script_length"] = latest_script.parameters.get("length", "60 seconds")
            
            if media_actions:
                latest_media = media_actions[-1]
                if latest_media.status == "completed":
                    self.agent_context.user_preferences["preferred_media_style"] = latest_media.parameters.get("style", "cinematic")
                    self.agent_context.user_preferences["preferred_media_count"] = latest_media.parameters.get("count", 8)
            
            if voiceover_actions:
                latest_voiceover = voiceover_actions[-1]
                if latest_voiceover.status == "completed":
                    self.agent_context.user_preferences["preferred_voiceover_voice"] = latest_voiceover.parameters.get("voice", "en-US-Neural2-A")
            
        except Exception as e:
            logger.error(f"Error updating user preferences: {e}")
    
    async def _check_task_completion(self, executed_actions: List[AgentAction]) -> Dict[str, Any]:
        """Enhanced task completion check with intelligent decision making"""
        try:
            # Analyze executed actions and their results
            successful_actions = [action for action in executed_actions if action.status == "completed"]
            failed_actions = [action for action in executed_actions if action.status == "failed"]
            
            # Get current project state
            project_state = self._format_project_state()
            
            # Check if we have the core components for a complete video
            has_script = any("script" in action.action_type.lower() for action in successful_actions)
            has_media = any("broll" in action.action_type.lower() or "media" in action.action_type.lower() for action in successful_actions)
            has_voiceover = any("voiceover" in action.action_type.lower() for action in successful_actions)
            has_video = any("video" in action.action_type.lower() or "processor" in action.action_type.lower() for action in successful_actions)
            
            # Intelligent completion logic
            completion_reasons = []
            missing_components = []
            
            # Check for video creation workflow
            if any("video" in action.description.lower() for action in executed_actions):
                if has_script and has_media and has_voiceover and has_video:
                    completion_reasons.append("Complete video workflow executed successfully")
                else:
                    if not has_script:
                        missing_components.append("script")
                    if not has_media:
                        missing_components.append("media")
                    if not has_voiceover:
                        missing_components.append("voiceover")
                    if not has_video:
                        missing_components.append("final video")
            
            # Check for script-only workflow
            elif any("script" in action.description.lower() for action in executed_actions):
                if has_script:
                    completion_reasons.append("Script created successfully")
                else:
                    missing_components.append("script")
            
            # Check for media-only workflow
            elif any("media" in action.description.lower() or "broll" in action.description.lower() for action in executed_actions):
                if has_media:
                    completion_reasons.append("Media collected successfully")
                else:
                    missing_components.append("media")
            
            # Check for conversational responses
            elif not executed_actions:
                completion_reasons.append("Conversational response completed")
            
            # Determine completion status
            is_completed = len(missing_components) == 0 and len(completion_reasons) > 0
            
            # Generate intelligent next suggestions
            next_suggestions = await self._generate_intelligent_suggestions(executed_actions, missing_components)
            
            # Create completion response
            completion_response = {
                "completed": is_completed,
                "reasons": completion_reasons,
                "missing_components": missing_components,
                "next_suggestions": next_suggestions,
                "confidence": len(successful_actions) / max(len(executed_actions), 1)
            }
            
            # Add final message
            if is_completed:
                if "video" in completion_reasons[0].lower():
                    completion_response["final_message"] = "🎉 Your video is complete! I've created a script, found relevant media, generated a voiceover, and assembled everything into a polished final video."
                elif "script" in completion_reasons[0].lower():
                    completion_response["final_message"] = "✅ Script created successfully! Would you like me to find some B-roll media to go with it?"
                elif "media" in completion_reasons[0].lower():
                    completion_response["final_message"] = "📸 Media collected successfully! Should I create a script that showcases these visuals?"
                else:
                    completion_response["final_message"] = "✅ Task completed successfully!"
            else:
                completion_response["final_message"] = f"I've made progress! {', '.join(completion_reasons)}. {'Missing: ' + ', '.join(missing_components) if missing_components else ''}"
            
            return completion_response
            
        except Exception as e:
            logger.error(f"Error checking task completion: {e}")
            return {
                "completed": False,
                "reasons": ["Error occurred during completion check"],
                "final_message": "I encountered an issue while checking completion. Let me know if you need anything else!"
            }
    
    async def _create_final_response(self, message: str, actions: List[AgentAction] = None) -> AgentResponse:
        """Create final response with proper formatting"""
        try:
            # Clean up the message to remove undefined
            if message and "undefined" in message:
                message = message.replace("undefined", "").strip()
            
            # If message is empty or just whitespace, provide a default
            if not message or not message.strip():
                if actions and len(actions) > 0:
                    message = "I've completed the requested tasks successfully!"
                else:
                    message = "I'm here to help you with video creation and general questions. What would you like to do?"
            
            # Create the response
            response = AgentResponse(
                message=message,
                actions=actions or [],
                context_updates={
                    "iteration": self.agent_context.iteration_count,
                    "actions_completed": len(actions) if actions else 0,
                    "final_response": True
                }
            )
            
            logger.info(f"Created final response: {message[:100]}...")
            return response
            
        except Exception as e:
            logger.error(f"Error creating final response: {e}")
            return AgentResponse(
                message="I'm here to help you with video creation and general questions. What would you like to do?",
                actions=[],
                context_updates={"error": str(e)}
            )
    
    async def _generate_next_suggestions(self) -> List[str]:
        """Generate intelligent next suggestions based on context and learning"""
        try:
            suggestions = []
            
            # Get current project state
            project_state = self._format_project_state()
            
            # Analyze what we have and what's missing
            has_script = "scripts" in self.agent_context.current_project and len(self.agent_context.current_project["scripts"]) > 0
            has_media = "media_files" in self.agent_context.current_project and len(self.agent_context.current_project["media_files"]) > 0
            has_voiceover = "voiceovers" in self.agent_context.current_project and len(self.agent_context.current_project["voiceovers"]) > 0
            has_video = "videos" in self.agent_context.current_project and len(self.agent_context.current_project["videos"]) > 0
            
            # Generate context-aware suggestions
            if has_script and not has_media:
                suggestions.extend([
                    "🎬 Find B-roll media to bring your script to life",
                    "🎵 Generate a voiceover for your script"
                ])
            
            if has_script and has_media and not has_voiceover:
                suggestions.extend([
                    "🎵 Generate a professional voiceover for your script",
                    "🎬 Create the final video with your script and media"
                ])
            
            if has_script and has_media and has_voiceover and not has_video:
                suggestions.append("🎬 Create the final video with all your content")
            
            if has_media and not has_script:
                suggestions.extend([
                    "✍️ Create a script that showcases your media",
                    "🎵 Generate a voiceover for your content"
                ])
            
            # Add learning-based suggestions
            if "successful_patterns" in self.agent_context.user_preferences:
                patterns = self.agent_context.user_preferences["successful_patterns"]
                if patterns:
                    # Suggest based on successful patterns
                    latest_pattern = patterns[-1]
                    if "script" in latest_pattern["action_type"]:
                        suggestions.append("🎬 Continue with media collection (based on your preferences)")
                    elif "broll" in latest_pattern["action_type"]:
                        suggestions.append("🎵 Generate voiceover (based on your preferences)")
            
            # Add general suggestions if we don't have enough
            if len(suggestions) < 2:
                suggestions.extend([
                    "✍️ Create a script about any topic",
                    "🎬 Find B-roll media for your project",
                    "🎵 Generate a professional voiceover",
                    "🎬 Create a complete video"
                ])
            
            return suggestions[:3]  # Limit to 3 suggestions
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            return ["Create a script", "Find B-roll media", "Generate a voiceover"] 

    async def _send_agent_state_update(self, state: str, message: str) -> None:
        """Send agent state update to frontend"""
        try:
            await self.websocket_manager.send_message(self.agent_context.session_id, {
                "type": "agent_state_update",
                "state": state,
                "message": message,
                "iteration": self.agent_context.iteration_count,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error sending agent state update: {e}")
    
    async def _send_action_start(self, action: AgentAction) -> None:
        """Send action start message"""
        try:
            await self.websocket_manager.send_message(self.agent_context.session_id, {
                "type": "action_start",
                "action_id": action.id,
                "action_type": action.action_type,
                "description": action.description,
                "parameters": action.parameters,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error sending action start: {e}")
    
    async def _send_action_complete(self, action: AgentAction) -> None:
        """Send action complete message"""
        try:
            await self.websocket_manager.send_message(self.agent_context.session_id, {
                "type": "action_complete",
                "action_id": action.id,
                "action_type": action.action_type,
                "result": action.result,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error sending action complete: {e}")
    
    async def _send_action_error(self, action: AgentAction) -> None:
        """Send action error message"""
        try:
            await self.websocket_manager.send_message(self.agent_context.session_id, {
                "type": "action_error",
                "action_id": action.id,
                "action_type": action.action_type,
                "error": action.error,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error sending action error: {e}")
    
    def _format_conversation_history(self) -> str:
        """Format conversation history"""
        try:
            if not self.agent_context.conversation_history:
                return "No conversation history"
            
            formatted = []
            for message in self.agent_context.conversation_history[-5:]:  # Last 5 messages
                role = message.get("role", "unknown")
                content = message.get("content", "")
                formatted.append(f"{role}: {content}")
            
            return "\n".join(formatted)
        except Exception as e:
            logger.error(f"Error formatting conversation history: {e}")
            return "Error formatting conversation history"
    
    def _format_project_state(self) -> str:
        """Format project state"""
        try:
            project = self.agent_context.current_project
            if not project:
                return "No project state"
            
            state_parts = []
            if project.get("scripts"):
                state_parts.append(f"Scripts: {len(project['scripts'])}")
            if project.get("media_files"):
                state_parts.append(f"Media: {len(project['media_files'])}")
            if project.get("voiceovers"):
                state_parts.append(f"Voiceovers: {len(project['voiceovers'])}")
            if project.get("videos"):
                state_parts.append(f"Videos: {len(project['videos'])}")
            
            return ", ".join(state_parts) if state_parts else "Empty project"
        except Exception as e:
            logger.error(f"Error formatting project state: {e}")
            return "Error formatting project state"
    
    def _format_recent_executions(self) -> str:
        """Format recent executions"""
        try:
            if not self.agent_context.tool_executions:
                return "No recent executions"
            
            formatted = []
            for execution in self.agent_context.tool_executions[-3:]:  # Last 3 executions
                status = "✅" if execution.error is None else "❌"
                formatted.append(f"{status} {execution.tool_name}: {execution.execution_time:.2f}s")
            
            return "\n".join(formatted)
        except Exception as e:
            logger.error(f"Error formatting recent executions: {e}")
            return "Error formatting recent executions"
    
    def _extract_json_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """Extract JSON tool calls from response"""
        tool_calls = []
        
        # Look for JSON blocks
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
        
        # If no JSON blocks found, try to extract from the response directly
        if not tool_calls:
            # Look for tool names in the response
            tool_names = ["script_writer", "broll_finder", "voiceover_generator", "video_processor"]
            for tool_name in tool_names:
                if tool_name in response.lower():
                    # Try to extract parameters
                    tool_call = {
                        "tool": tool_name,
                        "args": {},
                        "description": f"Using {tool_name} based on user request"
                    }
                    
                    # Extract topic if mentioned
                    if "romans" in response.lower():
                        tool_call["args"]["topic"] = "The Romans"
                    elif "messi" in response.lower():
                        tool_call["args"]["topic"] = "Lionel Messi"
                    
                    # Add style and length for script_writer
                    if tool_name == "script_writer":
                        tool_call["args"]["style"] = "cinematic"
                        tool_call["args"]["length"] = "60 seconds"
                    
                    # Add count for broll_finder
                    elif tool_name == "broll_finder":
                        tool_call["args"]["count"] = 8
                        tool_call["args"]["style"] = "cinematic"
                    
                    # Add voice for voiceover_generator
                    elif tool_name == "voiceover_generator":
                        tool_call["args"]["voice"] = "en-US-Neural2-A"
                        tool_call["args"]["style"] = "professional"
                    
                    # Add style for video_processor
                    elif tool_name == "video_processor":
                        tool_call["args"]["style"] = "cinematic"
                        tool_call["args"]["duration"] = "60 seconds"
                    
                    tool_calls.append(tool_call)
        
        logger.info(f"Extracted {len(tool_calls)} tool calls from response")
        return tool_calls

    async def _infer_actions_from_request(self) -> List[AgentAction]:
        """Infer actions from user request when no explicit tool calls are found"""
        try:
            actions = []
            user_message = self.agent_context.user_message.lower()
            
            # Check for script-related requests
            if any(keyword in user_message for keyword in ["script", "write", "create script"]):
                if "romans" in user_message:
                    action = AgentAction(
                        id=str(uuid.uuid4()),
                        action_type="script_writer",
                        description="Creating a script about The Romans",
                        parameters={
                            "topic": "The Romans",
                            "style": "cinematic",
                            "length": "60 seconds"
                        },
                        priority=1
                    )
                    actions.append(action)
                elif "messi" in user_message:
                    action = AgentAction(
                        id=str(uuid.uuid4()),
                        action_type="script_writer",
                        description="Creating a script about Lionel Messi",
                        parameters={
                            "topic": "Lionel Messi",
                            "style": "cinematic",
                            "length": "60 seconds"
                        },
                        priority=1
                    )
                    actions.append(action)
                else:
                    # Generic script request
                    action = AgentAction(
                        id=str(uuid.uuid4()),
                        action_type="script_writer",
                        description="Creating a script based on user request",
                        parameters={
                            "topic": "user topic",
                            "style": "cinematic",
                            "length": "60 seconds"
                        },
                        priority=1
                    )
                    actions.append(action)
            
            # Check for video-related requests
            elif any(keyword in user_message for keyword in ["video", "create video", "make video"]):
                # Create a multi-step workflow
                if "romans" in user_message:
                    # Step 1: Create script
                    script_action = AgentAction(
                        id=str(uuid.uuid4()),
                        action_type="script_writer",
                        description="Creating a script about The Romans",
                        parameters={
                            "topic": "The Romans",
                            "style": "cinematic",
                            "length": "60 seconds"
                        },
                        priority=1
                    )
                    actions.append(script_action)
                    
                    # Step 2: Find B-roll
                    broll_action = AgentAction(
                        id=str(uuid.uuid4()),
                        action_type="broll_finder",
                        description="Finding B-roll for The Romans",
                        parameters={
                            "topic": "The Romans",
                            "count": 8,
                            "style": "cinematic"
                        },
                        priority=2
                    )
                    actions.append(broll_action)
                    
                    # Step 3: Generate voiceover
                    voiceover_action = AgentAction(
                        id=str(uuid.uuid4()),
                        action_type="voiceover_generator",
                        description="Generating voiceover for The Romans script",
                        parameters={
                            "voice": "en-US-Neural2-A",
                            "style": "professional"
                        },
                        priority=3
                    )
                    actions.append(voiceover_action)
                    
                    # Step 4: Process video
                    video_action = AgentAction(
                        id=str(uuid.uuid4()),
                        action_type="video_processor",
                        description="Processing final video about The Romans",
                        parameters={
                            "style": "cinematic",
                            "duration": "60 seconds"
                        },
                        priority=4
                    )
                    actions.append(video_action)
            
            # Check for B-roll requests
            elif any(keyword in user_message for keyword in ["broll", "media", "images", "footage"]):
                action = AgentAction(
                    id=str(uuid.uuid4()),
                    action_type="broll_finder",
                    description="Finding B-roll media",
                    parameters={
                        "topic": "user topic",
                        "count": 8,
                        "style": "cinematic"
                    },
                    priority=1
                )
                actions.append(action)
            
            # Check for voiceover requests
            elif any(keyword in user_message for keyword in ["voiceover", "voice", "audio"]):
                action = AgentAction(
                    id=str(uuid.uuid4()),
                    action_type="voiceover_generator",
                    description="Generating voiceover",
                    parameters={
                        "voice": "en-US-Neural2-A",
                        "style": "professional"
                    },
                    priority=1
                )
                actions.append(action)
            
            logger.info(f"Inferred {len(actions)} actions from user request")
            return actions
            
        except Exception as e:
            logger.error(f"Error inferring actions: {e}")
            return [] 

    async def _generate_intelligent_suggestions(self, executed_actions: List[AgentAction], missing_components: List[str]) -> List[str]:
        """Generate intelligent suggestions based on executed actions and missing components"""
        try:
            suggestions = []
            
            # Analyze what we have
            has_script = any("script" in action.action_type.lower() for action in executed_actions)
            has_media = any("broll" in action.action_type.lower() or "media" in action.action_type.lower() for action in executed_actions)
            has_voiceover = any("voiceover" in action.action_type.lower() for action in executed_actions)
            has_video = any("video" in action.action_type.lower() or "processor" in action.action_type.lower() for action in executed_actions)
            
            # Generate context-aware suggestions
            if has_script and not has_media:
                suggestions.append("🎬 Find B-roll media to bring your script to life")
                suggestions.append("🎵 Generate a voiceover for your script")
            
            if has_script and has_media and not has_voiceover:
                suggestions.append("🎵 Generate a professional voiceover for your script")
                suggestions.append("🎬 Create the final video with your script and media")
            
            if has_script and has_media and has_voiceover and not has_video:
                suggestions.append("🎬 Create the final video with all your content")
            
            if has_media and not has_script:
                suggestions.append("✍️ Create a script that showcases your media")
                suggestions.append("🎵 Generate a voiceover for your content")
            
            if has_voiceover and not has_script:
                suggestions.append("✍️ Create a script to go with your voiceover")
                suggestions.append("🎬 Find B-roll media for your content")
            
            # Add general suggestions
            if not suggestions:
                suggestions.extend([
                    "✍️ Create a script about any topic",
                    "🎬 Find B-roll media for your project",
                    "🎵 Generate a professional voiceover",
                    "🎬 Create a complete video"
                ])
            
            return suggestions[:3]  # Limit to 3 suggestions
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            return ["Create a script", "Find B-roll media", "Generate a voiceover"] 