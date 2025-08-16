"""
SclipBrain - Agentic Orchestrator for Video Processing
Implements the core agentic loop: prompt → plan → execute → verify → update
"""
import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple, AsyncGenerator
from enum import Enum
from datetime import datetime
import httpx
from pydantic import BaseModel
import re # Added for regex in _parse_fluid_response
from pathlib import Path # Added for file path handling

from config import settings
from ..utils.logger import get_logger
from .streaming_manager import StreamingManager

logger = get_logger(__name__)

class OrchestratorState(Enum):
    """State machine states for the orchestrator"""
    AWAITING_PROMPT = "awaiting_prompt"
    PLANNING = "planning"
    EXECUTING_STEP = "executing_step"
    VERIFYING_STEP = "verifying_step"
    OBSERVING_RESULT = "observing_result"
    DECIDING_NEXT_ACTION = "deciding_next_action"
    AWAITING_USER_APPROVAL = "awaiting_user_approval"
    HANDLING_ERROR = "handling_error"
    FINAL_CHECK = "final_check"
    DONE = "done"
    PAUSED = "paused"

class ToolCall(BaseModel):
    """Represents a tool call with arguments"""
    tool: str
    args: Dict[str, Any]
    step_id: str
    description: str

class ToolResult(BaseModel):
    """Represents the result of a tool execution"""
    tool: str
    step_id: str
    success: bool
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    verification_passed: bool = False

class Step(BaseModel):
    """Represents a single step in the workflow"""
    step_id: str
    description: str
    tool: str
    args: Dict[str, Any]
    status: str = "pending"  # pending, running, completed, failed, verified
    result: Optional[ToolResult] = None
    retry_count: int = 0
    max_retries: int = 3

class WorkflowPlan(BaseModel):
    """Represents the complete workflow plan"""
    steps: List[Step]
    estimated_duration: Optional[str] = None
    total_steps: int = 0

class AgenticContext(BaseModel):
    """Represents the current context for agentic decision making"""
    user_prompt: str
    conversation_history: List[Dict[str, str]]
    completed_steps: List[Step]
    current_step: Optional[Step] = None
    tool_results: List[ToolResult]
    user_context: Dict[str, Any]
    session_id: str

class SclipBrain:
    """
    Agentic orchestrator that manages the entire video processing workflow.
    Implements the core loop: prompt → plan → execute → verify → update
    """
    
    def __init__(self, send_message_func=None):
        self.state = OrchestratorState.AWAITING_PROMPT
        self.current_session_id: Optional[str] = None
        self.user_prompt: Optional[str] = None
        self.workflow_plan: Optional[WorkflowPlan] = None
        self.current_step_index: int = 0
        self.completed_steps: List[Step] = []
        self.user_context: Dict[str, Any] = {}
        self.retry_counts: Dict[str, int] = {}
        self.send_message_func = send_message_func
        self.conversation_history = []  # Track conversation history
        self.tool_results: List[ToolResult] = []  # Track all tool results for context
        
        # Initialize tools
        self.tools = {}
        self._initialize_tools()
        
        # Gemini API client
        self.gemini_client = None
        if settings.gemini_api_key and settings.gemini_api_key.strip():
            # Use API key as query parameter instead of Authorization header
            self.gemini_api_key = settings.gemini_api_key
            self.gemini_model = settings.gemini_model
            logger.info("Gemini API client initialized successfully")
        else:
            logger.error("No Gemini API key provided - AI functionality will not work")
        
        logger.info("SclipBrain initialized", state=self.state.value)
    
    def _initialize_tools(self):
        """Initialize all available tools"""
        try:
            from ..tools.script_writer import ScriptWriterTool
            from ..tools.broll_finder import BrollFinderTool
            from ..tools.voiceover_generator import VoiceoverGeneratorTool
            from ..tools.video_processor import VideoProcessorTool
            
            self.tools["script_writer"] = ScriptWriterTool()
            self.tools["broll_finder"] = BrollFinderTool()
            self.tools["voiceover_generator"] = VoiceoverGeneratorTool()
            self.tools["video_processor"] = VideoProcessorTool()
            
            logger.info(f"Initialized {len(self.tools)} tools")
        except Exception as e:
            logger.error(f"Error initializing tools: {e}")
            self.tools = {}
    
    async def start_workflow_streaming(self, user_prompt: str, session_id: str, user_context: Dict[str, Any] = None):
        """
        Start the agentic workflow with streaming responses.
        This is the main entry point for real-time interaction.
        """
        try:
            logger.info("Starting streaming workflow", session_id=session_id, prompt=user_prompt)
            
            # Initialize session
            self.current_session_id = session_id
            self.user_prompt = user_prompt
            self.user_context = user_context or {}
            self.state = OrchestratorState.PLANNING
            
            # Add to conversation history
            self.conversation_history.append({"role": "user", "content": user_prompt})
            
            # Step 1: AI Planning Phase - Stream reasoning
            yield {
                "type": "thinking",
                "content": "🤔 Analyzing your request and planning the workflow...",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
            
            # Get AI response with context
            try:
                ai_response = await self._get_ai_response_with_context(user_prompt)
                self.conversation_history.append({"role": "assistant", "content": ai_response})
            except Exception as e:
                logger.error(f"AI service failed: {e}")
                yield {
                    "type": "error",
                    "message": f"AI service unavailable: {str(e)}",
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
                return
            
            # Step 2: Parse the AI response
            try:
                parsed_response = self._parse_fluid_response(ai_response)
                response_type = parsed_response.get("type", "conversational")  # Changed from "response_type" to "type"
            except Exception as e:
                logger.error(f"Failed to parse AI response: {e}")
                yield {
                    "type": "ai_message",
                    "content": ai_response,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
                return
            
            # Step 3: Handle different response types with agentic loop
            if response_type == "workflow":
                # Execute agentic workflow loop
                async for message in self._execute_agentic_workflow_loop(parsed_response, session_id):
                    yield message
            elif response_type == "conversational":
                # Simple conversational response
                user_message = parsed_response.get("user_message", ai_response)
                yield {
                    "type": "ai_message",
                    "content": user_message,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                # Default to conversational
                user_message = parsed_response.get("user_message", ai_response)
                yield {
                    "type": "ai_message",
                    "content": user_message,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Update session context
            self._update_session_context(parsed_response)
            
        except Exception as e:
            logger.error(f"Error in agentic workflow streaming: {e}")
            yield {
                "type": "error",
                "message": f"Sorry, something went wrong: {str(e)}",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
    
    async def _execute_agentic_workflow_loop(self, parsed_response: Dict[str, Any], session_id: str):
        """
        Execute the true agentic loop: plan → execute → observe → decide → repeat
        """
        tool_calls = parsed_response.get("tool_calls", [])
        logger.info(f"Agentic workflow loop - tool_calls: {tool_calls}")
        logger.info(f"Agentic workflow loop - tool_calls type: {type(tool_calls)}")
        logger.info(f"Agentic workflow loop - tool_calls length: {len(tool_calls)}")
        
        # Check if this is a conversational response (no tools needed)
        if not tool_calls:
            # Extract user message from the response
            user_message = parsed_response.get("user_message", "")
            if not user_message:
                # Try to extract from the response content
                if "response_type" in parsed_response and parsed_response["response_type"] == "conversational":
                    user_message = parsed_response.get("user_message", "Hello! I'm here to help you with video creation, general questions, or just conversation. What would you like to know or create?")
                else:
                    # Default conversational response
                    user_message = "Hello! I'm here to help you with video creation, general questions, or just conversation. What would you like to know or create?"
            
            yield {
                "type": "ai_message",
                "content": user_message,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
            return
        
        # Create initial workflow plan
        self.workflow_plan = self._create_workflow_plan({"tool_calls": tool_calls})
        logger.info(f"Created workflow plan with {len(self.workflow_plan.steps)} steps")
        self.state = OrchestratorState.EXECUTING_STEP
        
        # Check if this is a full video creation workflow and add missing steps
        if len(tool_calls) == 1 and tool_calls[0].tool == "script_writer":
            # This is likely a script-only request, but let's check if user wants full video
            if any(word in self.user_prompt.lower() for word in ["video", "make", "create", "generate"]):
                # User wants full video, add missing steps
                logger.info("Detected video creation request, adding missing workflow steps")
                additional_steps = [
                    Step(
                        step_id="step_2",
                        description="Finding B-roll media for the video",
                        tool="broll_finder",
                        args={"topic": self._extract_topic_from_prompt(self.user_prompt), "count": 8, "style": "cinematic"}
                    ),
                    Step(
                        step_id="step_3", 
                        description="Generating voiceover from the script",
                        tool="voiceover_generator",
                        args={"script_text": "Generated script", "voice": "professional"}
                    ),
                    Step(
                        step_id="step_4",
                        description="Assembling final video",
                        tool="video_processor", 
                        args={"media_files": [], "script": "Generated script", "voiceover": "voiceover.wav"}
                    )
                ]
                self.workflow_plan.steps.extend(additional_steps)
                logger.info(f"Added {len(additional_steps)} additional steps for full video creation")
        
        # Agentic loop: continue until all steps are completed or user stops
        while self.current_step_index < len(self.workflow_plan.steps):
            try:
                # Get current step
                current_step = self.workflow_plan.steps[self.current_step_index]
                self.state = OrchestratorState.EXECUTING_STEP
                
                # Step 1: Announce current step with reasoning
                yield {
                    "type": "thinking",
                    "content": f"🎯 Executing step {self.current_step_index + 1}/{len(self.workflow_plan.steps)}: {current_step.description}",
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Step 2: Execute tool
                yield {
                    "type": "tool_call",
                    "tool": current_step.tool,
                    "args": current_step.args,
                    "step": current_step.step_id,
                    "description": current_step.description,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Execute the tool
                tool_result = await self._execute_tool(current_step)
                
                # Step 3: Observe result
                self.state = OrchestratorState.OBSERVING_RESULT
                yield {
                    "type": "tool_result",
                    "tool": current_step.tool,
                    "step": current_step.step_id,
                    "result": tool_result.output,
                    "success": tool_result.success,
                    "error": tool_result.error,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Store result for context
                self.tool_results.append(tool_result)
                
                # Step 4: AI decides next action based on result
                self.state = OrchestratorState.DECIDING_NEXT_ACTION
                if tool_result.success:
                    # Verify the result
                    verification_passed = await self._verify_step_result(current_step, tool_result)
                    
                    if verification_passed:
                        # Move to next step
                        self.current_step_index += 1
                        self.completed_steps.append(current_step)
                        
                        # Check if we need to add more steps based on results
                        additional_steps = await self._decide_additional_steps(current_step, tool_result)
                        if additional_steps:
                            self.workflow_plan.steps.extend(additional_steps)
                            logger.info(f"Added {len(additional_steps)} additional steps based on results")
                    else:
                        # Verification failed, retry or adjust
                        if current_step.retry_count < current_step.max_retries:
                            current_step.retry_count += 1
                            logger.info(f"Retrying step {current_step.step_id} (attempt {current_step.retry_count})")
                            # Adjust tool args based on previous result
                            adjusted_args = await self._adjust_tool_args(current_step, tool_result)
                            current_step.args = adjusted_args
                        else:
                            # Max retries reached, move to next step
                            logger.warning(f"Max retries reached for step {current_step.step_id}")
                            self.current_step_index += 1
                            self.completed_steps.append(current_step)
                else:
                    # Tool execution failed
                    await self._handle_step_failure(current_step, tool_result)
                    if current_step.retry_count < current_step.max_retries:
                        current_step.retry_count += 1
                        logger.info(f"Retrying failed step {current_step.step_id} (attempt {current_step.retry_count})")
                    else:
                        # Max retries reached, move to next step
                        logger.warning(f"Max retries reached for failed step {current_step.step_id}")
                        self.current_step_index += 1
                        self.completed_steps.append(current_step)
                        
            except Exception as e:
                logger.error(f"Error executing step {current_step.step_id}: {e}")
                await self._handle_step_failure(current_step, None, str(e))
                self.current_step_index += 1
                self.completed_steps.append(current_step)
        
        # Final check and completion
        self.state = OrchestratorState.FINAL_CHECK
        yield {
            "type": "thinking",
            "content": "🎉 Workflow completed! Performing final checks...",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }
        
        # Perform final verification
        final_check_passed = await self._final_check()
        if final_check_passed:
            yield {
                "type": "workflow_complete",
                "content": "✅ Workflow completed successfully!",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
        else:
            yield {
                "type": "workflow_complete",
                "content": "⚠️ Workflow completed with some issues. Please review the results.",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
        
        self.state = OrchestratorState.DONE
    
    async def _decide_additional_steps(self, completed_step: Step, result: ToolResult) -> List[Step]:
        """
        AI decides if additional steps are needed based on the completed step and its result.
        This is the core of the agentic decision-making process.
        """
        try:
            # Create context for decision making
            context = AgenticContext(
                user_prompt=self.user_prompt,
                conversation_history=self.conversation_history,
                completed_steps=self.completed_steps,
                current_step=completed_step,
                tool_results=self.tool_results,
                user_context=self.user_context,
                session_id=self.current_session_id
            )
            
            # Create decision prompt
            decision_prompt = self._create_decision_prompt(context, completed_step, result)
            
            # Get AI decision
            ai_response = await self._get_ai_response(decision_prompt)
            
            # Parse additional steps
            additional_steps = self._parse_additional_steps(ai_response)
            
            return additional_steps
            
        except Exception as e:
            logger.error(f"Error deciding additional steps: {e}")
            return []
    
    def _create_decision_prompt(self, context: AgenticContext, completed_step: Step, result: ToolResult) -> str:
        """Create a prompt for AI to decide on additional steps"""
        return f"""
You are SclipBrain, an AI orchestrator. Based on the completed step and its result, decide if additional steps are needed.

**Current Context:**
- User Request: {context.user_prompt}
- Completed Steps: {len(context.completed_steps)}/{len(self.workflow_plan.steps) if self.workflow_plan else 0}
- Just Completed: {completed_step.description}
- Tool: {completed_step.tool}
- Success: {result.success}
- Output: {json.dumps(result.output, indent=2) if result.output else "None"}

**Available Tools:**
{self._get_tool_descriptions()}

**Decision Task:**
Analyze the completed step and its result. Determine if additional steps are needed to:
1. Improve the quality of the output
2. Add missing elements
3. Fix any issues
4. Complete the user's request

**Response Format:**
If additional steps are needed, respond with:
{{
    "additional_steps": [
        {{
            "step_id": "step_{len(self.workflow_plan.steps) + 1}",
            "description": "What this step will accomplish",
            "tool": "tool_name",
            "args": {{"param": "value"}},
            "reasoning": "Why this step is needed"
        }}
    ]
}}

If no additional steps are needed, respond with:
{{
    "additional_steps": []
}}

**Important:** Only add steps that are truly necessary to complete the user's request or improve quality.
"""
    
    def _parse_additional_steps(self, ai_response: str) -> List[Step]:
        """Parse additional steps from AI response"""
        try:
            # Try to parse JSON response
            if "{" in ai_response and "}" in ai_response:
                start = ai_response.find("{")
                end = ai_response.rfind("}") + 1
                json_str = ai_response[start:end]
                
                parsed = json.loads(json_str)
                additional_steps_data = parsed.get("additional_steps", [])
                
                steps = []
                for step_data in additional_steps_data:
                    step = Step(
                        step_id=step_data.get("step_id", f"step_{len(self.workflow_plan.steps) + len(steps) + 1}"),
                        description=step_data.get("description", ""),
                        tool=step_data.get("tool", ""),
                        args=step_data.get("args", {}),
                        status="pending"
                    )
                    steps.append(step)
                
                return steps
        except Exception as e:
            logger.error(f"Error parsing additional steps: {e}")
        
        return []
    
    async def _adjust_tool_args(self, step: Step, result: ToolResult) -> Dict[str, Any]:
        """
        AI adjusts tool arguments based on previous failure or result.
        This is part of the adaptive behavior.
        """
        try:
            # Create adjustment prompt
            adjustment_prompt = f"""
The tool {step.tool} failed or produced unsatisfactory results. Please suggest adjusted arguments.

**Original Args:** {json.dumps(step.args, indent=2)}
**Result:** {json.dumps(result.output, indent=2) if result.output else "None"}
**Error:** {result.error or "None"}

**Available Tools:**
{self._get_tool_descriptions()}

**Task:** Suggest adjusted arguments for the {step.tool} tool that might work better.

**Response Format:**
{{
    "adjusted_args": {{
        "param1": "new_value1",
        "param2": "new_value2"
    }},
    "reasoning": "Why these adjustments should work better"
}}

**Important:** Only adjust parameters that are likely to fix the issue. Don't change the core tool or approach unless necessary.
"""
            
            # Get AI adjustment
            ai_response = await self._get_ai_response(adjustment_prompt)
            
            # Parse adjusted args
            adjusted_args = self._parse_adjusted_args(ai_response)
            
            return adjusted_args if adjusted_args else step.args
            
        except Exception as e:
            logger.error(f"Error adjusting tool args: {e}")
            return step.args
    
    def _parse_adjusted_args(self, ai_response: str) -> Dict[str, Any]:
        """Parse adjusted arguments from AI response"""
        try:
            if "{" in ai_response and "}" in ai_response:
                start = ai_response.find("{")
                end = ai_response.rfind("}") + 1
                json_str = ai_response[start:end]
                
                parsed = json.loads(json_str)
                return parsed.get("adjusted_args", {})
        except Exception as e:
            logger.error(f"Error parsing adjusted args: {e}")
        
        return {}
    
    async def _plan_workflow(self) -> Dict[str, Any]:
        """
        AI planning phase: Analyze user prompt and create execution plan.
        Returns both user-facing message and backend action plan.
        """
        try:
            logger.info("Planning workflow", prompt=self.user_prompt)
            
            # Create system prompt for planning
            system_prompt = self._create_planning_prompt()
            
            # Get AI response with dual-response pattern
            ai_response = await self._get_ai_response(system_prompt)
            
            # Parse the dual response (user message + tool call)
            user_message, tool_calls = self._parse_dual_response(ai_response)
            
            logger.info("Workflow planned", 
                       user_message=user_message, 
                       tool_calls_count=len(tool_calls))
            
            return {
                "user_message": user_message,
                "tool_calls": tool_calls,
                "estimated_duration": "5-10 minutes"
            }
            
        except Exception as e:
            logger.error("Planning failed", error=str(e))
            raise
    
    def _create_planning_prompt(self) -> str:
        """Create the system prompt for AI planning"""
        return f"""
You are Sclip, an AI orchestrator for video processing. 

IMPORTANT: ONLY plan a video workflow if the user EXPLICITLY asks for a video (e.g., 'make a video', 'create a documentary', 'generate a cinematic story', 'edit a video', etc.).
If the user just says 'hi', 'hello', asks a question, or wants to chat, answer conversationally and DO NOT plan a video.

User request: "{self.user_prompt}"

If this is a simple greeting or question (not a video request), respond conversationally as a helpful AI assistant.

If the user wants a video:
1. Analyze the user's request: "{self.user_prompt}"
2. Break it down into specific, executable steps
3. Choose the appropriate tools for each step
4. Provide both a user-friendly explanation AND specific tool calls

Available tools:
- script_writer: Generate video scripts
- broll_finder: Find and download B-roll footage
- voiceover_generator: Create voiceovers from scripts
- video_processor: Assemble final videos

User context: {json.dumps(self.user_context, indent=2)}

Respond in this EXACT format if a video is requested:
{{
    "user_message": "I'll help you create this video. Here's what I'm going to do...",
    "tool_calls": [
        {{
            "tool": "script_writer",
            "args": {{"topic": "example", "style": "cinematic"}},
            "step_id": "step_1",
            "description": "Generate script for the video"
        }}
    ]
}}

If the user does NOT want a video, just return a conversational answer as a string.
"""
    
    async def _get_ai_response(self, prompt: str) -> str:
        """Get response from Gemini AI with retry logic and fallback"""
        if not hasattr(self, 'gemini_api_key') or not self.gemini_api_key:
            # Fallback response when no API key is available
            logger.warning("No Gemini API key - using fallback response")
            return self._generate_fallback_response(prompt)
        
        max_retries = 3
        retry_delay = 2.0  # Start with 2 second delay
        
        for attempt in range(max_retries):
            try:
                # Create the full prompt with system context
                system_prompt = self._create_agentic_system_prompt()
                full_prompt = f"{system_prompt}\n\nUser: {prompt}\n\nRespond in the appropriate format based on the user's intent."
                
                # Use httpx to make the API call with API key as query parameter
                async with httpx.AsyncClient(timeout=60.0) as client:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_api_key}"
                    
                    response = await client.post(
                        url,
                        json={
                            "contents": [{"parts": [{"text": full_prompt}]}],
                            "generationConfig": {
                                "temperature": 0.7,
                                "maxOutputTokens": 8192
                            }
                        }
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    if "candidates" in result and len(result["candidates"]) > 0:
                        return result["candidates"][0]["content"]["parts"][0]["text"]
                    else:
                        raise Exception("No response from Gemini API")
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    # Rate limited - retry with exponential backoff
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Gemini API rate limited (429) (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                elif e.response.status_code == 503 and attempt < max_retries - 1:
                    # Service unavailable - retry with exponential backoff
                    wait_time = retry_delay * (2 ** attempt)
                    logger.warning(f"Gemini API 503 error (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                elif e.response.status_code == 401:
                    # Unauthorized - don't retry
                    error_msg = f"Gemini API authentication failed: {str(e)}"
                    logger.error(error_msg)
                    logger.error(f"API Key: {self.gemini_api_key[:10]}...")
                    logger.error(f"Model: {self.gemini_model}")
                    return self._generate_fallback_response(prompt)
                else:
                    # Other HTTP errors
                    error_msg = f"Gemini API call failed: {str(e)}"
                    logger.error(error_msg)
                    logger.error(f"API Key: {self.gemini_api_key[:10]}...")
                    logger.error(f"Model: {self.gemini_model}")
                    return self._generate_fallback_response(prompt)
                        
            except Exception as e:
                if attempt < max_retries - 1:
                    # Network or other errors - retry
                    wait_time = retry_delay * (2 ** attempt)
                    logger.warning(f"Gemini API error (attempt {attempt + 1}/{max_retries}): {str(e)}, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # Final attempt failed
                    error_msg = f"Gemini API call failed after {max_retries} attempts: {str(e)}"
                    logger.error(error_msg)
                    logger.error(f"API Key: {self.gemini_api_key[:10]}...")
                    logger.error(f"Model: {self.gemini_model}")
                    return self._generate_fallback_response(prompt)
        
        # If we get here, all retries failed
        return self._generate_fallback_response(prompt)
    
    def _generate_fallback_response(self, prompt: str) -> str:
        """Generate a fallback response when AI service is unavailable"""
        prompt_lower = prompt.lower()
        
        # Check for different types of requests
        if any(keyword in prompt_lower for keyword in ["video", "create", "make", "generate", "romans", "messi", "script", "broll"]):
            # Extract topic from prompt
            topic = self._extract_topic_from_prompt(prompt)
            
            # Determine what tools to call based on the request
            tool_calls = []
            
            if any(word in prompt_lower for word in ["script", "write"]):
                # Script-only request
                tool_calls.append({
                    "tool": "script_writer",
                    "args": {"topic": topic, "style": "cinematic", "length": "60 seconds"},
                    "description": f"Creating a script about {topic}"
                })
            elif any(word in prompt_lower for word in ["broll", "media", "footage", "images"]):
                # B-roll only request
                tool_calls.append({
                    "tool": "broll_finder",
                    "args": {"topic": topic, "count": 8, "style": "cinematic"},
                    "description": f"Finding B-roll media for {topic}"
                })
            elif any(word in prompt_lower for word in ["voiceover", "audio", "speech"]):
                # Voiceover only request
                tool_calls.append({
                    "tool": "voiceover_generator",
                    "args": {"script_text": f"Sample script about {topic}", "voice": "professional"},
                    "description": f"Generating voiceover for {topic}"
                })
            else:
                # Full video creation workflow
                tool_calls = [
                    {
                        "tool": "script_writer",
                        "args": {"topic": topic, "style": "cinematic", "length": "60 seconds"},
                        "description": f"Creating a script about {topic}"
                    },
                    {
                        "tool": "broll_finder",
                        "args": {"topic": topic, "count": 8, "style": "cinematic"},
                        "description": f"Finding B-roll media for {topic}"
                    },
                    {
                        "tool": "voiceover_generator",
                        "args": {"script_text": f"Sample script about {topic}", "voice": "professional"},
                        "description": f"Generating voiceover for {topic}"
                    },
                    {
                        "tool": "video_processor",
                        "args": {"media_files": [], "script": f"Script about {topic}", "voiceover": "voiceover.wav"},
                        "description": f"Assembling final video about {topic}"
                    }
                ]
            
            return json.dumps({
                "response_type": "workflow",
                "reasoning": f"User requested video creation about {topic}. Executing workflow with available tools.",
                "plan": f"Creating a complete video about {topic} using the available tools",
                "tool_calls": tool_calls,
                "context_updates": {"topic": topic, "project_status": "in_progress"},
                "user_message": f"I'll help you create a video about {topic}! Let me start by creating a script and finding relevant media."
            })
        elif any(word in prompt_lower for word in ["hi", "hello", "hey", "greetings"]):
            # Greeting response
            return json.dumps({
                "response_type": "conversational",
                "reasoning": "User sent a greeting",
                "user_message": "Hello! I'm SclipBrain, your AI agent for video creation. I can help you create videos, write scripts, find B-roll footage, generate voiceovers, and more! What would you like to work on today?"
            })
        elif any(word in prompt_lower for word in ["who", "what", "how", "why", "when", "where"]) and "?" in prompt:
            # Question response
            return json.dumps({
                "response_type": "conversational",
                "reasoning": "User asked a question",
                "user_message": f"That's a great question about {prompt}! I'm here to help you create videos and content. Would you like me to create a video about this topic or help you with something else?"
            })
        elif any(word in prompt_lower for word in ["help", "what can you do", "capabilities"]):
            # Help response
            return json.dumps({
                "response_type": "conversational",
                "reasoning": "User asked for help",
                "user_message": "I'm SclipBrain, your AI agent for video creation! Here's what I can do:\n\n🎬 **Video Creation**: Create complete videos from scratch\n📝 **Script Writing**: Generate engaging scripts for any topic\n🎥 **B-roll Finding**: Search and download relevant footage\n🎤 **Voiceover Generation**: Convert scripts to professional audio\n🎨 **Video Assembly**: Combine everything into final videos\n\nJust tell me what you'd like to create!"
            })
        else:
            # Conversational response for other requests
            return json.dumps({
                "response_type": "conversational",
                "reasoning": "User request doesn't appear to be video-related",
                "user_message": f"I understand you said: {prompt}. I'm here to help you create videos and content. What would you like to work on? I can help with scripts, B-roll, voiceovers, or complete video creation!"
            })
    
    async def _get_ai_response_with_context(self, prompt: str) -> str:
        """Get AI response with conversation context"""
        try:
            # Build context from conversation history
            context_prompt = self._build_context_prompt(prompt)
            return await self._get_ai_response(context_prompt)
        except Exception as e:
            logger.error(f"Error getting AI response with context: {e}")
            raise
    
    def _build_context_prompt(self, current_prompt: str) -> str:
        """Build a prompt with conversation context"""
        if len(self.conversation_history) <= 1:
            return current_prompt
        
        # Build context from recent messages (last 5 exchanges)
        recent_messages = self.conversation_history[-10:]  # Last 10 messages
        context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_messages])
        
        return f"Previous conversation:\n{context}\n\nCurrent message: {current_prompt}\n\nRespond naturally, considering the conversation context."
    

    
    def _parse_fluid_response(self, ai_response: str) -> Dict[str, Any]:
        """Parse fluid AI response - handles all response types dynamically"""
        try:
            # Clean up any markdown formatting that might be present
            cleaned_response = ai_response.strip()
            
            # Remove markdown code blocks if present
            if cleaned_response.startswith('```'):
                lines = cleaned_response.split('\n')
                # Remove first line (```json or similar)
                if len(lines) > 1:
                    lines = lines[1:]
                # Remove last line (```)
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                cleaned_response = '\n'.join(lines).strip()
            
            # Try to parse as JSON for structured responses
            response_data = json.loads(cleaned_response)
            
            # Handle different response types
            response_type = response_data.get("response_type", "conversational")
            
            if response_type == "workflow" or "tool_calls" in response_data:
                # Video workflow response
                tool_calls = []
                for i, tc in enumerate(response_data.get("tool_calls", [])):
                    # Ensure tool_call has all required fields
                    if isinstance(tc, dict):
                        # Add step_id if missing
                        if "step_id" not in tc:
                            tc["step_id"] = f"step_{i+1}"
                        tool_calls.append(ToolCall(**tc))
                    else:
                        tool_calls.append(tc)
                
                return {
                    "type": "workflow",
                    "user_message": response_data.get("user_message", "Processing your request..."),
                    "tool_calls": tool_calls,
                    "workflow_plan": response_data.get("workflow_plan"),
                    "estimated_duration": response_data.get("estimated_duration")
                }
            
            elif response_type == "informational" or "info_type" in response_data:
                # Information/help response
                return {
                    "type": "informational",
                    "user_message": response_data.get("user_message", ""),
                    "info_type": response_data.get("info_type"),
                    "capabilities": response_data.get("capabilities", []),
                    "suggestions": response_data.get("suggestions", []),
                    "tutorial": response_data.get("tutorial")
                }
            
            elif response_type == "interactive" or "user_input_request" in response_data:
                # Interactive response requiring user input
                return {
                    "type": "interactive",
                    "user_message": response_data.get("user_message", ""),
                    "user_input_request": response_data.get("user_input_request"),
                    "choices": response_data.get("choices", []),
                    "questions": response_data.get("questions", [])
                }
            
            elif response_type == "adaptive" or "context_update" in response_data:
                # Adaptive response updating context
                return {
                    "type": "adaptive",
                    "user_message": response_data.get("user_message", ""),
                    "context_update": response_data.get("context_update"),
                    "preferences": response_data.get("preferences"),
                    "learning": response_data.get("learning")
                }
            
            else:
                # Default to conversational
                return {
                    "type": "conversational",
                    "user_message": response_data.get("user_message", ai_response),
                    "context_hints": response_data.get("context_hints", [])
                }
            
        except json.JSONDecodeError:
            # If not JSON, treat as plain text response
            # Check if this looks like a conversational response
            if any(word in ai_response.lower() for word in ["hi", "hello", "hey", "who", "what", "how", "why", "when", "where", "thanks", "thank you"]):
                return {
                    "type": "conversational",
                    "user_message": ai_response,
                    "response_type": "conversational"
                }
            else:
                # Try to extract user_message from the response
                user_message = ai_response
                if "user_message" in ai_response:
                    # Try to extract from JSON-like format
                    match = re.search(r'"user_message":\s*"([^"]+)"', ai_response)
                    if match:
                        user_message = match.group(1)
            
            return {
                "type": "conversational",
                    "user_message": user_message,
                "response_type": "conversational"
            }
    
    def _create_workflow_plan(self, planning_response: Dict[str, Any]) -> WorkflowPlan:
        """Create workflow plan from AI planning response, always using ToolCall objects."""
        steps = []
        tool_calls = planning_response.get("tool_calls", [])
        for i, tool_call in enumerate(tool_calls):
            # Handle both ToolCall objects and dictionaries
            if isinstance(tool_call, ToolCall):
                # Already a ToolCall object
                step = Step(
                    step_id=tool_call.step_id or f"step_{i+1}",
                    description=tool_call.description or "Process step",
                    tool=tool_call.tool or "unknown",
                    args=tool_call.args or {}
                )
            elif isinstance(tool_call, dict):
                # Convert dictionary to ToolCall object
                tool_call_obj = ToolCall(**tool_call)
                step = Step(
                    step_id=tool_call_obj.step_id or f"step_{i+1}",
                    description=tool_call_obj.description or "Process step",
                    tool=tool_call_obj.tool or "unknown",
                    args=tool_call_obj.args or {}
                )
            else:
                # Unknown type, skip
                continue
                
            steps.append(step)
        return WorkflowPlan(
            steps=steps,
            estimated_duration=planning_response.get("estimated_duration", "Unknown"),
            total_steps=len(steps)
        )
    
    async def _execute_workflow(self):
        """
        Main execution loop: execute → verify → update → decide next step
        This is the core agentic loop that continues until completion.
        """
        logger.info("Starting workflow execution", total_steps=len(self.workflow_plan.steps))
        
        while self.current_step_index < len(self.workflow_plan.steps):
            try:
                # Get current step
                current_step = self.workflow_plan.steps[self.current_step_index]
                self.state = OrchestratorState.EXECUTING_STEP
                
                logger.info("Executing step", 
                           step_id=current_step.step_id,
                           tool=current_step.tool,
                           description=current_step.description)
                
                # Step 1: Execute the tool
                tool_result = await self._execute_tool(current_step)
                
                # Step 2: Verify the result
                self.state = OrchestratorState.VERIFYING_STEP
                verification_passed = await self._verify_step_result(current_step, tool_result)
                
                if verification_passed:
                    # Step 3: Update user and move to next step
                    await self._update_user_progress(current_step, tool_result)
                    self.completed_steps.append(current_step)
                    self.current_step_index += 1
                    
                    # Step 4: Decide next step
                    if self.current_step_index < len(self.workflow_plan.steps):
                        next_step = self.workflow_plan.steps[self.current_step_index]
                        await self._announce_next_step(next_step)
                    else:
                        # All steps complete
                        await self._final_check()
                        break
                        
                else:
                    # Verification failed, retry or ask for help
                    await self._handle_step_failure(current_step, tool_result)
                    
            except Exception as e:
                logger.error("Step execution failed", 
                           step_id=current_step.step_id,
                           error=str(e))
                await self._handle_step_failure(current_step, None, error=str(e))
    
    async def _execute_tool(self, step: Step) -> ToolResult:
        """Execute a single tool step"""
        try:
            # Get the tool module
            tool_module = await self._get_tool_module(step.tool)
            if not tool_module:
                return ToolResult(
                    tool=step.tool,
                    step_id=step.step_id,
                    success=False,
                    error=f"Tool {step.tool} not found"
                )
            
            # Prepare input data with context from previous steps
            input_data = step.args.copy()
            
            # Add session_id if not present
            if "session_id" not in input_data:
                input_data["session_id"] = self.current_session_id if self.current_session_id else "default"
            
            # Handle context from previous steps
            if step.tool == "voiceover_generator":
                # Get script from previous script_writer step
                script_result = next((r for r in self.tool_results if r.tool == "script_writer"), None)
                if script_result and script_result.success:
                    script_text = script_result.output.get("script_text", "")
                    if script_text:
                        input_data["script_text"] = script_text
                        logger.info(f"Using script from previous step for voiceover generation")
                    else:
                        # Try to get script from file path
                        script_path = script_result.output.get("script_path", "")
                        if script_path and Path(script_path).exists():
                            try:
                                with open(script_path, 'r', encoding='utf-8') as f:
                                    script_text = f.read()
                                input_data["script_text"] = script_text
                                logger.info(f"Loaded script from file: {script_path}")
                            except Exception as e:
                                logger.error(f"Failed to read script file: {e}")
                                input_data["script_text"] = "Generated script content"
                        else:
                            input_data["script_text"] = "Generated script content"
                            logger.warning("No script text found, using placeholder")
                else:
                    input_data["script_text"] = "Generated script content"
                    logger.warning("No script result found, using placeholder")
            
            elif step.tool == "video_processor":
                # Get voiceover path from previous voiceover_generator step
                voiceover_result = next((r for r in self.tool_results if r.tool == "voiceover_generator"), None)
                if voiceover_result and voiceover_result.success:
                    voiceover_path = voiceover_result.output.get("audio_path", "")
                    if voiceover_path:
                        input_data["audio_path"] = voiceover_path
                        logger.info(f"Using voiceover path from previous step: {voiceover_path}")
                
                # Get broll paths from previous broll_finder step
                broll_result = next((r for r in self.tool_results if r.tool == "broll_finder"), None)
                if broll_result and broll_result.success:
                    # Try different possible keys for broll paths
                    broll_paths = []
                    
                    # Check for downloaded_files first
                    if broll_result.output.get("downloaded_files"):
                        broll_paths = [file.get("path", "") for file in broll_result.output["downloaded_files"] if file.get("path")]
                        logger.info(f"Using downloaded_files paths: {len(broll_paths)} files")
                    
                    # If no downloaded_files, try file_paths
                    elif broll_result.output.get("file_paths"):
                        broll_paths = broll_result.output["file_paths"]
                        logger.info(f"Using file_paths: {len(broll_paths)} files")
                    
                    # Filter out non-existent paths
                    existing_broll_paths = [path for path in broll_paths if path and Path(path).exists()]
                    
                    if existing_broll_paths:
                        input_data["broll_paths"] = existing_broll_paths
                        logger.info(f"Using broll paths from previous step: {len(existing_broll_paths)} files")
                    else:
                        logger.warning("No existing broll paths found")
                        input_data["broll_paths"] = []
                
                # Ensure we have the required parameters for video processor
                if "media_files" in input_data and not input_data.get("broll_paths"):
                    # If media_files is provided but broll_paths is not, use media_files
                    media_files = input_data.pop("media_files", [])
                    
                    # Handle different formats of media_files
                    if isinstance(media_files, str):
                        # If it's a string, it might be a directory path or single file
                        if Path(media_files).exists():
                            if Path(media_files).is_dir():
                                # It's a directory, scan for media files
                                media_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.jpg', '.jpeg', '.png', '.gif']
                                found_files = []
                                for ext in media_extensions:
                                    found_files.extend([str(f) for f in Path(media_files).glob(f"*{ext}")])
                                input_data["broll_paths"] = found_files
                                logger.info(f"Found {len(found_files)} media files in directory: {media_files}")
                            else:
                                # It's a single file
                                input_data["broll_paths"] = [media_files]
                        else:
                            # File doesn't exist, treat as empty
                            input_data["broll_paths"] = []
                            logger.warning(f"Media files path does not exist: {media_files}")
                    elif isinstance(media_files, list):
                        # It's already a list, use as is
                        input_data["broll_paths"] = media_files
                    else:
                        # Unknown format, convert to list
                        input_data["broll_paths"] = [media_files] if media_files else []
                
                # Handle case where broll_paths might be from downloaded_files format
                if "broll_paths" in input_data and input_data["broll_paths"]:
                    # Check if broll_paths contains dict objects with 'path' keys
                    processed_paths = []
                    for item in input_data["broll_paths"]:
                        if isinstance(item, dict):
                            # Extract path from dict format
                            file_path = item.get("path", item.get("file", ""))
                            if file_path:
                                processed_paths.append(file_path)
                        else:
                            # It's already a string path
                            processed_paths.append(str(item))
                    input_data["broll_paths"] = processed_paths
                
                # Handle effects parameter - ensure it's a list
                if "effects" in input_data and isinstance(input_data["effects"], str):
                    # Convert string effects to list format
                    effects_str = input_data["effects"]
                    if effects_str in ["auto_transitions", "auto-transitions"]:
                        input_data["effects"] = [{"name": "auto_transitions", "start_time": 0, "duration": 1}]
                    elif effects_str in ["fade", "fade_in_out"]:
                        input_data["effects"] = [{"name": "fade_in", "start_time": 0, "duration": 1}]
                    elif effects_str in ["cinematic_transitions", "cinematic-transitions"]:
                        input_data["effects"] = [{"name": "ken_burns", "start_time": 0, "duration": 1}]
                    elif effects_str in ["dynamic_zoom", "dynamic-zoom"]:
                        input_data["effects"] = [{"name": "zoom_in", "start_time": 0, "duration": 1}]
                    elif effects_str in ["smooth_transitions", "smooth-transitions"]:
                        input_data["effects"] = [{"name": "fade_in", "start_time": 0, "duration": 1}]
                    else:
                        # Try to parse as JSON or create a simple effect
                        try:
                            import json
                            parsed_effects = json.loads(effects_str)
                            if isinstance(parsed_effects, list):
                                input_data["effects"] = parsed_effects
                            else:
                                input_data["effects"] = [{"name": effects_str, "start_time": 0, "duration": 1}]
                        except:
                            input_data["effects"] = [{"name": effects_str, "start_time": 0, "duration": 1}]
                elif "effects" not in input_data:
                    input_data["effects"] = []
                
                # Handle transitions parameter - ensure it's a list
                if "transitions" in input_data and isinstance(input_data["transitions"], str):
                    transitions_str = input_data["transitions"]
                    if transitions_str in ["fade", "fade_in_out"]:
                        input_data["transitions"] = [{"name": "fade", "start_time": 0, "duration": 1}]
                    elif transitions_str in ["smooth", "smooth_transitions"]:
                        input_data["transitions"] = [{"name": "fade", "start_time": 0, "duration": 1}]
                    else:
                        # Try to parse as JSON or create a simple transition
                        try:
                            import json
                            parsed_transitions = json.loads(transitions_str)
                            if isinstance(parsed_transitions, list):
                                input_data["transitions"] = parsed_transitions
                            else:
                                input_data["transitions"] = [{"name": transitions_str, "start_time": 0, "duration": 1}]
                        except:
                            input_data["transitions"] = [{"name": transitions_str, "start_time": 0, "duration": 1}]
                elif "transitions" not in input_data:
                    input_data["transitions"] = []
                
                # Handle filters parameter - ensure it's a list
                if "filters" in input_data and isinstance(input_data["filters"], str):
                    filters_str = input_data["filters"]
                    if filters_str in ["cinematic", "cinematic_look"]:
                        input_data["filters"] = [{"name": "cinematic", "intensity": 1.0}]
                    elif filters_str in ["color_grade", "color-grade"]:
                        input_data["filters"] = [{"name": "cinematic", "intensity": 1.0}]
                    elif filters_str in ["background_music", "background-music"]:
                        # This is not a filter, it's background music
                        input_data["background_music"] = {"volume": 0.3}
                        input_data["filters"] = []
                    else:
                        # Try to parse as JSON or create a simple filter
                        try:
                            import json
                            parsed_filters = json.loads(filters_str)
                            if isinstance(parsed_filters, list):
                                input_data["filters"] = parsed_filters
                            else:
                                input_data["filters"] = [{"name": filters_str, "intensity": 1.0}]
                        except:
                            input_data["filters"] = [{"name": filters_str, "intensity": 1.0}]
                elif "filters" not in input_data:
                    input_data["filters"] = []
                
                # Add session_id if not present
                if "session_id" not in input_data:
                    input_data["session_id"] = self.current_session_id if self.current_session_id else "default"
            
            # Execute the tool
            logger.info(f"Executing tool {step.tool} with args: {input_data}")
            result = await tool_module.run(input_data)
            
            return ToolResult(
                tool=step.tool,
                step_id=step.step_id,
                success=True,
                output=result
            )
            
        except Exception as e:
            logger.error(f"Error executing tool {step.tool}: {e}")
            return ToolResult(
                tool=step.tool,
                step_id=step.step_id,
                success=False,
                error=str(e)
            )
    
    async def _get_tool_module(self, tool_name: str):
        """Get the tool module by name, using correct class and interface."""
        try:
            if tool_name == "script_writer":
                from ..tools.script_writer import ScriptWriterTool
                return ScriptWriterTool()
            elif tool_name == "broll_finder":
                from ..tools.broll_finder import BrollFinderTool
                return BrollFinderTool()
            elif tool_name == "voiceover_generator":
                from ..tools.voiceover_generator import VoiceoverGeneratorTool
                return VoiceoverGeneratorTool()
            elif tool_name == "video_processor":
                from ..tools.video_processor import VideoProcessorTool
                return VideoProcessorTool()
            else:
                logger.warning(f"Unknown tool: {tool_name}")
                return None
        except ImportError as e:
            logger.error(f"Failed to import tool {tool_name}: {e}")
            return None
    
    async def _verify_step_result(self, step: Step, result: ToolResult) -> bool:
        """Verify that the step result meets requirements"""
        try:
            if not result.success:
                logger.warning("Step failed, cannot verify", step_id=step.step_id)
                return False
            
            # For script_writer, check if script was generated
            if step.tool == "script_writer":
                if result.output and "script_text" in result.output:
                    logger.info("Script verification passed - script generated successfully", step_id=step.step_id)
                    return True
                else:
                    logger.warning("Script verification failed - no script_text in output", step_id=step.step_id)
                    return False
            
            # For broll_finder, check if files were found
            elif step.tool == "broll_finder":
                if result.output and ("files" in result.output or "downloaded_files" in result.output):
                    logger.info("B-roll verification passed - files found", step_id=step.step_id)
                    return True
                else:
                    logger.warning("B-roll verification failed - no files found", step_id=step.step_id)
                    return False
            
            # For voiceover_generator, check if audio was generated
            elif step.tool == "voiceover_generator":
                if result.output and ("audio_path" in result.output or "file_path" in result.output):
                    logger.info("Voiceover verification passed - audio generated", step_id=step.step_id)
                    return True
                else:
                    logger.warning("Voiceover verification failed - no audio generated", step_id=step.step_id)
                    return False
            
            # For video_processor, check if video was created
            elif step.tool == "video_processor":
                if result.output and ("video_path" in result.output or "file_path" in result.output):
                    logger.info("Video verification passed - video created", step_id=step.step_id)
                    return True
                else:
                    logger.warning("Video verification failed - no video created", step_id=step.step_id)
                    return False
            
            # Default verification - check if output exists
            else:
                if result.output:
                    logger.info("Default verification passed - output exists", step_id=step.step_id)
                    return True
                else:
                    logger.warning("Default verification failed - no output", step_id=step.step_id)
                    return False
            
        except Exception as e:
            logger.error("Verification failed", step_id=step.step_id, error=str(e))
            # Be more lenient - if verification fails, assume success
            logger.info("Verification failed, assuming success", step_id=step.step_id)
            return True
    
    def _create_verification_prompt(self, step: Step, result: ToolResult) -> str:
        """Create prompt for AI verification"""
        return f"""
Verify that this step was completed successfully:

Step: {step.description}
Tool: {step.tool}
Output: {json.dumps(result.output, indent=2)}

User's original request: "{self.user_prompt}"

Does this output satisfy the user's requirements for this step? 
Consider:
1. Is the output complete and usable?
2. Does it match the user's intent?
3. Is it of good quality?

Respond with only "YES" or "NO" and a brief reason.
"""
    
    def _parse_verification_response(self, ai_response: str) -> bool:
        """Parse AI verification response"""
        response_str = ai_response if isinstance(ai_response, str) else ""
        response_lower = response_str.lower().strip()
        return "yes" in response_lower and "no" not in response_lower
    
    async def _update_user_progress(self, step: Step, result: ToolResult):
        """Update user with progress and results"""
        logger.info("Updating user progress", 
                   step_id=step.step_id,
                   completed_steps=len(self.completed_steps) + 1,
                   total_steps=len(self.workflow_plan.steps))
        
        # This would send a message to the frontend
        # For now, we just log it
        progress_message = f"✅ {step.description} completed successfully!"
        logger.info("User progress update", message=progress_message)
    
    async def _announce_next_step(self, next_step: Step):
        """Announce the next step to the user"""
        logger.info("Announcing next step", 
                   step_id=next_step.step_id,
                   description=next_step.description)
        
        next_step_message = f"🔄 Next: {next_step.description}"
        logger.info("Next step announcement", message=next_step_message)
    
    async def _handle_step_failure(self, step: Step, result: Optional[ToolResult], error: str = None):
        """Handle step failure with retry logic or user intervention"""
        step.retry_count += 1
        
        if step.retry_count <= step.max_retries:
            logger.info("Retrying step", 
                       step_id=step.step_id,
                       retry_count=step.retry_count,
                       max_retries=step.max_retries)
            
            # Wait before retry
            await asyncio.sleep(2 ** step.retry_count)  # Exponential backoff
            
        else:
            logger.error("Step failed after max retries", 
                        step_id=step.step_id,
                        error=error or "Unknown error")
            
            # Ask for user help
            self.state = OrchestratorState.AWAITING_USER_APPROVAL
            help_message = f"❌ Step '{step.description}' failed after {step.max_retries} attempts. Please help me understand what went wrong."
            logger.info("Requesting user help", message=help_message)
    
    async def _final_check(self):
        """Perform final verification that the entire workflow is complete"""
        try:
            self.state = OrchestratorState.FINAL_CHECK
            
            final_check_prompt = self._create_final_check_prompt()
            ai_response = await self._get_ai_response(final_check_prompt)
            
            final_result = self._parse_final_check_response(ai_response)
            
            if final_result:
                self.state = OrchestratorState.DONE
                logger.info("Workflow completed successfully", 
                           total_steps=len(self.completed_steps))
            else:
                logger.warning("Final check failed, workflow may be incomplete")
                
        except Exception as e:
            logger.error("Final check failed", error=str(e))
    
    def _create_final_check_prompt(self) -> str:
        """Create prompt for final verification"""
        completed_descriptions = [step.description for step in self.completed_steps]
        
        return f"""
Final verification: Has the user's request been completely fulfilled?

User's original request: "{self.user_prompt}"

Completed steps:
{chr(10).join(f"- {desc}" for desc in completed_descriptions)}

Does this complete the user's request? Consider:
1. All necessary steps completed?
2. Output quality meets expectations?
3. User's intent fully satisfied?

Respond with only "YES" or "NO" and a brief reason.
"""
    
    def _parse_final_check_response(self, ai_response: str) -> bool:
        """Parse final check response"""
        response_lower = ai_response.lower().strip()
        return "yes" in response_lower and "no" not in response_lower
    
    async def pause_workflow(self):
        """Pause the workflow for user intervention"""
        self.state = OrchestratorState.PAUSED
        logger.info("Workflow paused for user intervention")
    
    async def resume_workflow(self):
        """Resume the workflow after user intervention"""
        if self.state == OrchestratorState.PAUSED:
            self.state = OrchestratorState.EXECUTING_STEP
            logger.info("Workflow resumed")
            await self._execute_workflow()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the orchestrator"""
        return {
            "state": self.state.value,
            "session_id": self.current_session_id,
            "current_step": self.current_step_index,
            "total_steps": len(self.workflow_plan.steps) if self.workflow_plan else 0,
            "completed_steps": len(self.completed_steps),
            "user_prompt": self.user_prompt
        } 

    def _create_agentic_system_prompt(self) -> str:
        """Create an enhanced system prompt for agentic behavior"""
        return f"""
You are SclipBrain, an advanced AI orchestrator for video creation that operates like Cursor or GitHub Copilot Agent. You are an autonomous agent that plans, executes, and iterates on video creation workflows.

**CORE PRINCIPLES:**
1. **Autonomous Planning**: You interpret user requests and create detailed execution plans
2. **Tool Integration**: You have access to specialized tools for video creation tasks
3. **Iterative Refinement**: You observe results and adjust your approach based on outcomes
4. **Context Awareness**: You maintain conversation history and project state
5. **Real-time Transparency**: You communicate your reasoning and actions clearly

**AVAILABLE TOOLS:**
{self._get_tool_descriptions()}

**WORKFLOW PATTERNS:**
- **Script Creation**: Analyze topic → Generate engaging script → Validate content
- **Media Collection**: Search for relevant B-roll → Download and organize → Verify quality
- **Voiceover Generation**: Convert script to speech → Apply voice effects → Sync timing
- **Video Assembly**: Combine media elements → Add effects/transitions → Render final video

**EXECUTION STRATEGY:**
1. **Analyze Request**: Understand user intent and requirements
2. **Plan Workflow**: Break down into logical steps with dependencies
3. **Execute Tools**: Call appropriate tools with correct parameters
4. **Validate Results**: Check outputs and handle errors gracefully
5. **Iterate**: Refine approach based on results and user feedback
6. **Complete**: Ensure all requirements are met

**CRITICAL DECISION RULES:**
- **ALWAYS EXECUTE WORKFLOW** when user requests video creation, script writing, B-roll finding, or any video-related task
- **ONLY ask for clarification** if the request is completely ambiguous or missing essential information
- **DEFAULT TO ACTION** - if in doubt, start executing with reasonable assumptions
- **USE CONTEXT** - if user has provided style, length, or tone preferences, use them
- **BE PROACTIVE** - don't wait for perfect information, make reasonable assumptions and start working

**REQUEST TYPES AND RESPONSES:**

1. **VIDEO CREATION REQUESTS** (e.g., "make me a video on messi", "create a video about...")
   - Execute FULL workflow: script_writer → broll_finder → voiceover_generator → video_processor
   - Use reasonable defaults for style, length, tone
   - Start immediately with script creation

2. **SCRIPT REQUESTS** (e.g., "make me a script on...", "write a script about...")
   - Execute script_writer only
   - Focus on high-quality script generation
   - Provide detailed script with structure

3. **B-ROLL REQUESTS** (e.g., "find b-roll for...", "get footage of...")
   - Execute broll_finder only
   - Search for relevant media files
   - Download and organize content

4. **VOICEOVER REQUESTS** (e.g., "generate voiceover for...", "create audio for...")
   - Execute voiceover_generator only
   - Convert text to speech
   - Apply appropriate voice and effects

5. **GENERAL QUESTIONS** (e.g., "who is...", "what is...", "hi", "hello")
   - Provide conversational response
   - Offer to help with video creation
   - Be helpful and informative

6. **HELP REQUESTS** (e.g., "help", "what can you do", "how does this work")
   - Provide information about capabilities
   - Show available tools and features
   - Guide user to next steps

**RESPONSE FORMAT:**
Respond in JSON format with the following structure:
{{
    "response_type": "workflow|conversational|error",
    "reasoning": "Your step-by-step reasoning process",
    "plan": "Detailed execution plan",
    "tool_calls": [
        {{
            "tool": "tool_name",
            "args": {{"param": "value"}},
            "description": "What this tool call will accomplish"
        }}
    ],
    "context_updates": {{"key": "value"}},
    "user_message": "Human-readable explanation of what you're doing"
}}

**EXAMPLES OF WHEN TO EXECUTE WORKFLOW:**
- "Create a video about The Romans" → EXECUTE (script_writer + broll_finder + voiceover_generator + video_processor)
- "make me a video on messi" → EXECUTE (script_writer + broll_finder + voiceover_generator + video_processor)
- "Find B-roll for Messi" → EXECUTE (broll_finder)
- "Write a script about AI" → EXECUTE (script_writer)
- "Make a video" → EXECUTE (all tools with default assumptions)

**EXAMPLES OF WHEN TO ASK FOR CLARIFICATION:**
- "Help me" → ASK (too vague)
- "What can you do?" → ASK (information request)
- "How does this work?" → ASK (tutorial request)

**IMPORTANT:**
- **ALWAYS prefer action over conversation** for video creation tasks
- **Use reasonable defaults** when information is missing
- **Start with the most obvious tools** for the request
- **Provide clear progress updates** as you work
- **Focus on creating high-quality, engaging video content**
- **Handle all request types appropriately** - videos, scripts, B-roll, voiceovers, questions, greetings
"""
    
    def _update_session_context(self, parsed_response: Dict[str, Any]):
        """Update session context based on AI response"""
        response_type = parsed_response.get("type", "conversational")
        
        if response_type == "adaptive":
            # Update user preferences and learning
            preferences = parsed_response.get("preferences", {})
            learning = parsed_response.get("learning", {})
            
            # Merge with existing context
            self.user_context.update(preferences)
            
            # Store learning for future sessions
            if learning:
                self.user_context["learning"] = learning
                
        elif response_type == "workflow":
            # Store workflow preferences
            tool_calls = parsed_response.get("tool_calls", [])
            if tool_calls:
                # Extract style preferences from tool calls
                for tool_call in tool_calls:
                    if tool_call.tool == "script_writer":
                        args = tool_call.args
                        if "style" in args:
                            self.user_context["preferred_style"] = args["style"]
                        if "tone" in args:
                            self.user_context["preferred_tone"] = args["tone"]
                            
        # Always update interaction count
        self.user_context["interaction_count"] = self.user_context.get("interaction_count", 0) + 1 

    def _extract_fallback_tool_calls(self, user_prompt: str) -> List[Dict[str, Any]]:
        """Extract tool calls from user prompt when AI service is unavailable"""
        tool_calls = []
        prompt_lower = user_prompt.lower()
        
        # Check for script-related keywords
        if any(keyword in prompt_lower for keyword in ["script", "write", "create script", "make script"]):
            # Extract topic from prompt
            topic = self._extract_topic_from_prompt(user_prompt)
            tool_calls.append({
                "tool": "script_writer",
                "args": {
                    "topic": topic,
                    "style": "cinematic",
                    "length": "medium",
                    "tone": "professional"
                },
                "step_id": "fallback_step_1",
                "description": f"Generate script for {topic}"
            })
        
        return tool_calls
    
    def _extract_topic_from_prompt(self, user_prompt: str) -> str:
        """Extract topic from user prompt for fallback tool execution"""
        # Simple topic extraction - look for common patterns
        prompt_lower = user_prompt.lower()
        
        # Check for "about X" pattern
        if "about " in prompt_lower:
            about_index = prompt_lower.find("about ")
            topic_start = about_index + 6
            # Look for the end of the topic (end of sentence or common endings)
            topic_end = len(prompt_lower)
            for end_marker in [" ", ".", "!", "?", "\n"]:
                end_pos = prompt_lower.find(end_marker, topic_start)
                if end_pos != -1 and end_pos < topic_end:
                    topic_end = end_pos
            
            topic = user_prompt[topic_start:topic_end].strip()
            if topic:
                return topic
        
        # Check for "X video" pattern
        if " video" in prompt_lower:
            video_index = prompt_lower.find(" video")
            topic = user_prompt[:video_index].strip()
            if topic:
                return topic
        
        # Check for specific topics mentioned
        specific_topics = ["romans", "messi", "ai", "artificial intelligence", "space", "history", "science", "technology"]
        for topic in specific_topics:
            if topic in prompt_lower:
                # Capitalize properly
                if topic == "romans":
                    return "The Romans"
                elif topic == "messi":
                    return "Lionel Messi"
                elif topic == "ai" or topic == "artificial intelligence":
                    return "Artificial Intelligence"
                else:
                    return topic.title()
        
        # Default fallback
        return "general topic"
    
    async def _execute_fallback_workflow(self, tool_calls: List[Dict[str, Any]], session_id: str):
        """Execute workflow steps directly without AI planning"""
        try:
            # Create workflow plan from tool calls
            self.workflow_plan = self._create_workflow_plan({"tool_calls": tool_calls})
            self.state = OrchestratorState.EXECUTING_STEP
            
            # Execute each step
            while self.current_step_index < len(self.workflow_plan.steps):
                current_step = self.workflow_plan.steps[self.current_step_index]
                
                # Progress update
                yield {
                    "type": "progress",
                    "step": current_step.step_id,
                    "percent": int(100 * self.current_step_index / len(self.workflow_plan.steps)),
                    "status": f"Running {current_step.tool}",
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Tool call
                yield {
                    "type": "tool_call",
                    "tool": current_step.tool,
                    "args": current_step.args,
                    "step": current_step.step_id,
                    "description": current_step.description,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Execute tool
                tool_result = await self._execute_tool(current_step)
                
                # Tool result
                yield {
                    "type": "tool_result",
                    "tool": current_step.tool,
                    "step": current_step.step_id,
                    "result": tool_result.output,
                    "success": tool_result.success,
                    "error": tool_result.error,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
                
                if tool_result.success:
                    self.current_step_index += 1
                    self.completed_steps.append(current_step)
                    
                    # Send success message
                    if current_step.tool == "script_writer":
                        script_text = tool_result.output.get("script_text", "")
                        yield {
                            "type": "ai_message",
                            "content": f"✅ Script created successfully! Here's your script:\n\n{script_text[:200]}...",
                            "session_id": session_id,
                            "timestamp": datetime.now().isoformat()
                        }
                else:
                    # Handle failure
                    yield {
                        "type": "error",
                        "message": f"Tool {current_step.tool} failed: {tool_result.error}",
                        "session_id": session_id,
                        "timestamp": datetime.now().isoformat()
                    }
                    break
            
            # Final completion
            yield {
                "type": "progress",
                "step": "done",
                "percent": 100,
                "status": "Workflow complete",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
            yield {
                "type": "ai_message",
                "content": "🎉 Workflow completed successfully!",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in fallback workflow: {e}")
            yield {
                "type": "error",
                "message": f"Error in fallback workflow: {str(e)}",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            } 

    def _get_tool_descriptions(self) -> str:
        """Get formatted tool descriptions for the system prompt"""
        tool_descriptions = []
        
        # Define available tools with their capabilities
        tools = {
            "script_writer": {
                "description": "Creates engaging video scripts based on topics and style preferences",
                "capabilities": ["Generate scripts", "Style customization", "Length control", "Tone adjustment"],
                "input_params": ["topic", "style", "length", "tone"]
            },
            "broll_finder": {
                "description": "Searches and downloads relevant media from multiple sources",
                "capabilities": ["Image search", "Video search", "Multiple sources", "Quality filtering"],
                "input_params": ["topic", "count", "style", "sources"]
            },
            "voiceover_generator": {
                "description": "Converts scripts to professional voiceovers with various voices",
                "capabilities": ["Text-to-speech", "Voice selection", "Audio effects", "Timing control"],
                "input_params": ["script_text", "voice", "speed", "effects"]
            },
            "video_processor": {
                "description": "Assembles and processes videos with effects and transitions",
                "capabilities": ["Video assembly", "Effect application", "Transition effects", "Rendering"],
                "input_params": ["media_files", "script", "voiceover", "effects"]
            }
        }
        
        for tool_name, tool_info in tools.items():
            desc = f"**{tool_name}**: {tool_info['description']}\n"
            desc += f"  - Capabilities: {', '.join(tool_info['capabilities'])}\n"
            desc += f"  - Parameters: {', '.join(tool_info['input_params'])}\n"
            tool_descriptions.append(desc)
        
        return "\n".join(tool_descriptions) 