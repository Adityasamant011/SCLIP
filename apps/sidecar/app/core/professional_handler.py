"""
Professional Message Handler
Integrates AI Agent with proper context management and GUI updates
"""

import asyncio
import json
import uuid
from typing import Dict, Any, Optional, Set, List
from datetime import datetime

from .ai_agent import AIAgent, AIAgentFactory, AgentContext, AgentResponse
from .context_manager import context_manager
from .video_orchestrator import VideoEditingOrchestrator
from .streaming_communication import StreamingCommunicationManager, MessageType
from ..orchestrator.sclip_brain import SclipBrain
from ..tools.script_writer import ScriptWriterTool
from ..tools.broll_finder import BrollFinderTool
from ..tools.voiceover_generator import VoiceoverGeneratorTool
from ..tools.video_processor import VideoProcessorTool
from ..utils.logger import get_logger

logger = get_logger(__name__)

class ProfessionalMessageHandler:
    """Professional message handler with enhanced context awareness and GUI state management"""
    
    def __init__(self, websocket_manager, ai_service, script_writer, broll_finder, 
                 voiceover_generator, video_processor, project_scanner=None, video_viewer=None):
        
        self.websocket_manager = websocket_manager
        self.ai_service = ai_service
        self.script_writer = script_writer
        self.broll_finder = broll_finder
        self.voiceover_generator = voiceover_generator
        self.video_processor = video_processor
        self.project_scanner = project_scanner
        self.video_viewer = video_viewer
        self.agents: Dict[str, AIAgent] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.sent_messages: Dict[str, Set[str]] = {}  # Track sent messages per session
        
        # Initialize AI agent factory with all tools
        self.agent_factory = AIAgentFactory(
            ai_service=ai_service,
            script_writer=script_writer,
            broll_finder=broll_finder,
            voiceover_generator=voiceover_generator,
            video_processor=video_processor,
            websocket_manager=websocket_manager,
            project_scanner=project_scanner,
            video_viewer=video_viewer
        )
        
        # Initialize orchestrators for each session
        self.orchestrators: Dict[str, VideoEditingOrchestrator] = {}
        
        # Initialize streaming communication manager
        self.streaming_manager = StreamingCommunicationManager(websocket_manager)
        
        # Register message handlers
        self._register_message_handlers()
    
    def _register_message_handlers(self) -> None:
        """Register handlers for different message types"""
        
        # Register suggestion handler
        self.streaming_manager.register_message_handler(
            MessageType.SUGGESTION,
            self._handle_suggestion_message
        )
        
        # Register context update handler
        self.streaming_manager.register_message_handler(
            MessageType.CONTEXT_UPDATE,
            self._handle_context_update
        )
    
    async def _handle_suggestion_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """Handle suggestion messages from frontend"""
        suggestion_type = message.get("data", {}).get("suggestion_type")
        action = message.get("data", {}).get("action")
        
        if action and suggestion_type == "next_step":
            # Auto-execute suggested action
            agent = self.agents.get(session_id)
            if agent:
                await self._execute_suggested_action(session_id, action, agent)
    
    async def _handle_context_update(self, session_id: str, message: Dict[str, Any]) -> None:
        """Handle context update messages from frontend"""
        context_data = message.get("data", {}).get("data", {})
        context_type = message.get("data", {}).get("context_type")
        
        # Update agent context
        agent = self.agents.get(session_id)
        if agent and context_data:
            if context_type == "project_state":
                agent.context.current_project.update(context_data)
            elif context_type == "user_preferences":
                agent.context.user_preferences.update(context_data)
    
    async def _execute_suggested_action(self, session_id: str, action: str, agent: AIAgent) -> None:
        """Execute a suggested action automatically"""
        
        # Create action object
        action_obj = type('Action', (), {
            'action_type': action,
            'description': f"Executing suggested action: {action}",
            'parameters': {}
        })()
        
        # Execute the action
        try:
            result = await self._execute_action(action_obj, agent)
            
            # Send success message
            await self._send_unique_message(session_id, {
                "type": "suggestion_executed",
                "action": action,
                "result": "success",
                "message": f"✅ Executed suggested action: {action}",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            # Send error message
            await self._send_unique_message(session_id, {
                "type": "suggestion_error",
                "action": action,
                "error": str(e),
                "message": f"❌ Failed to execute suggested action: {action}",
                "timestamp": datetime.now().isoformat()
            })
    
    async def handle_message(self, session_id: str, message: str) -> None:
        """Handle incoming messages with enhanced agentic capabilities"""
        
        # Update context with user message
        context_manager.update_conversation_history(session_id, "user", message)
        
        # Check if this should trigger an agentic workflow
        if self._should_trigger_agentic_workflow(message):
            await self._handle_agentic_workflow(session_id, message)
        else:
            # Use existing conversational flow
            await self._handle_conversational_message(session_id, message)
    
    def _should_trigger_agentic_workflow(self, message: str) -> bool:
        """Determine if message should trigger agentic workflow"""
        # Keywords that indicate complex video creation tasks
        agentic_keywords = [
            "make me a video", "create a video", "generate a video",
            "make me a script", "create a script", "write a script", "write me a script",
            "make me a messi script", "create a messi script", "write a messi script",
            "find broll", "download media", "get footage",
            "generate voiceover", "create voiceover", "add voice",
            "edit video", "process video", "render video",
            "do it", "execute", "start", "begin"
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in agentic_keywords)
    
    async def _handle_agentic_workflow(self, session_id: str, message: str) -> None:
        """Handle message with agentic workflow orchestrator"""
        
        # Send initial response
        await self.websocket_manager.send_message(session_id, {
            "type": "message",
            "role": "assistant",
            "content": f"I'll help you with that! Let me analyze your request and create a comprehensive workflow to {message.lower()}.",
            "timestamp": datetime.now().isoformat()
        })
        
        try:
            # For script generation, use the existing script writer tool directly
            if "script" in message.lower():
                await self._handle_script_generation(session_id, message)
            else:
                # Create and execute agentic workflow for other tasks
                from ..orchestrator.agentic_workflow import agentic_orchestrator
                
                workflow_id = await agentic_orchestrator.create_workflow(session_id, message, self.websocket_manager)
                result = await agentic_orchestrator.execute_workflow(workflow_id)
                
                # Send completion message
                await self.websocket_manager.send_message(session_id, {
                    "type": "message",
                    "role": "assistant",
                    "content": f"✅ Workflow completed successfully! I've processed your request: '{message}'. The video creation process has been executed with {result.get('steps_completed', 0)} steps completed.",
                    "timestamp": datetime.now().isoformat()
                })
                
                # Update context with workflow results
                context_manager.update_workflow_results(session_id, workflow_id, result)
            
        except Exception as e:
            logger.error(f"Agentic workflow failed: {e}")
            
            # Send error message
            await self.websocket_manager.send_message(session_id, {
                "type": "message",
                "role": "assistant",
                "content": f"I encountered an issue while processing your request. Let me try a different approach or you can ask me to break this down into smaller steps.",
                "timestamp": datetime.now().isoformat()
            })
    
    async def _handle_script_generation(self, session_id: str, message: str) -> None:
        """Handle script generation with proper GUI updates"""
        try:
            # Extract topic from message
            message_lower = message.lower()
            if "messi" in message_lower:
                topic = "Lionel Messi"
            elif "romans" in message_lower:
                topic = "The Romans"
            elif "script" in message_lower:
                # Extract topic from the message more intelligently
                words = message.split()
                script_index = -1
                for i, word in enumerate(words):
                    if "script" in word.lower():
                        script_index = i
                        break
                
                if script_index >= 0 and script_index + 2 < len(words):
                    # Get words after "script on" or "script about"
                    if script_index + 1 < len(words) and words[script_index + 1].lower() in ["on", "about"]:
                        topic = " ".join(words[script_index + 2:])
                    else:
                        topic = " ".join(words[script_index + 1:])
                else:
                    topic = "user topic"
            else:
                topic = "user topic"
            
            # Send tool call message
            await self.websocket_manager.send_message(session_id, {
                "type": "tool_call",
                "tool": "script_writer",
                "args": {"topic": topic, "style": "cinematic", "length": "60 seconds"},
                "description": f"Creating a script about {topic}",
                "timestamp": datetime.now().isoformat()
            })
            
            # Execute script generation
            script_result = await self.script_writer.run({
                "topic": topic,
                "style": "cinematic",
                "length": "60 seconds",
                "tone": "professional"
            })
            
            # Check if script generation was successful
            if script_result and "script_text" in script_result:
                script_content = script_result.get("script_text", "")
                
                # Send tool result message
                await self.websocket_manager.send_message(session_id, {
                    "type": "tool_result",
                    "tool": "script_writer",
                    "success": True,
                    "result": script_result,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Send GUI update for script
                await self.websocket_manager.send_message(session_id, {
                    "type": "gui_update",
                    "update_type": "script_created",
                    "data": {
                        "script_content": script_content
                    },
                    "timestamp": datetime.now().isoformat()
                })
                
                # Send completion message
                await self.websocket_manager.send_message(session_id, {
                    "type": "message",
                    "role": "assistant",
                    "content": f"✅ Script created successfully! I've generated a cinematic script about {topic}. The script is now available in the script tab and ready for your review.",
                    "timestamp": datetime.now().isoformat()
                })
                
                # Update context
                context_manager.update_session_context(session_id, {
                    "current_script": script_content,
                    "script_topic": topic
                })
                
            else:
                # Send error message
                await self.websocket_manager.send_message(session_id, {
                    "type": "tool_result",
                    "tool": "script_writer",
                    "success": False,
                    "error": "Script generation failed - no script text returned",
                    "timestamp": datetime.now().isoformat()
                })
                
                await self.websocket_manager.send_message(session_id, {
                    "type": "message",
                    "role": "assistant",
                    "content": f"❌ I encountered an issue while creating the script. Please try again or let me know if you'd like to try a different approach.",
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Script generation failed: {e}")
            
            await self.websocket_manager.send_message(session_id, {
                "type": "message",
                "role": "assistant",
                "content": f"❌ I encountered an error while generating the script: {str(e)}. Please try again.",
                "timestamp": datetime.now().isoformat()
            })
    
    async def _handle_conversational_message(self, session_id: str, message: str) -> None:
        """Handle conversational messages with existing flow"""
        
        # Get enhanced context for better AI responses
        context = context_manager.get_enhanced_context_for_ai(session_id, message)
        
        # Create enhanced prompt
        enhanced_prompt = f"""
**ENHANCED CONVERSATIONAL CONTEXT**

**User Message:** {message}

**Full Context:**
{context}

**Available Tools:**
{self._get_tool_descriptions()}

**Response Guidelines:**
1. Be conversational and helpful
2. If the user wants to create content, suggest using agentic workflows
3. Provide specific, actionable advice
4. Reference previous context when relevant
5. Suggest next steps or improvements

Please respond naturally and conversationally.
"""
        
        # Send to AI for response
        response = await self._get_ai_response(enhanced_prompt, session_id)
        
        # Check if response contains JSON with tool calls
        if self._contains_tool_calls(response):
            # Execute the tool calls
            await self._execute_tool_calls_from_response(session_id, response, message)
        else:
            # Update context
            context_manager.update_conversation_history(session_id, "assistant", response)
            
            # Send response
            await self.websocket_manager.send_message(session_id, {
                "type": "message",
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now().isoformat()
            })
    
    def _contains_tool_calls(self, response: str) -> bool:
        """Check if response contains JSON with tool calls"""
        try:
            if "```json" in response:
                json_text = response.split("```json")[1].split("```")[0].strip()
                data = json.loads(json_text)
                return "tool_calls" in data and len(data["tool_calls"]) > 0
            return False
        except:
            return False
    
    async def _execute_tool_calls_from_response(self, session_id: str, response: str, original_message: str) -> None:
        """Execute tool calls from JSON response"""
        try:
            # Extract JSON from response
            json_text = response.split("```json")[1].split("```")[0].strip()
            data = json.loads(json_text)
            
            # Send initial response message
            user_message = data.get("user_message", "I'll execute the requested actions.")
            await self.websocket_manager.send_message(session_id, {
                "type": "message",
                "role": "assistant",
                "content": user_message,
                "timestamp": datetime.now().isoformat()
            })
            
            # Execute each tool call
            tool_calls = data.get("tool_calls", [])
            for tool_call in tool_calls:
                tool_name = tool_call.get("tool")
                args = tool_call.get("args", {})
                description = tool_call.get("description", "")
                
                # Send tool call message
                await self.websocket_manager.send_message(session_id, {
                    "type": "tool_call",
                    "tool": tool_name,
                    "args": args,
                    "description": description,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Execute the tool
                if tool_name == "script_writer":
                    await self._execute_script_writer_tool(session_id, args, description)
                elif tool_name == "broll_finder":
                    await self._execute_broll_finder_tool(session_id, args, description)
                elif tool_name == "voiceover_generator":
                    await self._execute_voiceover_generator_tool(session_id, args, description)
                elif tool_name == "video_processor":
                    await self._execute_video_processor_tool(session_id, args, description)
                else:
                    # Send error for unknown tool
                    await self.websocket_manager.send_message(session_id, {
                        "type": "tool_result",
                        "tool": tool_name,
                        "success": False,
                        "error": f"Unknown tool: {tool_name}",
                        "timestamp": datetime.now().isoformat()
                    })
            
            # Update context
            context_manager.update_conversation_history(session_id, "assistant", user_message)
            
        except Exception as e:
            logger.error(f"Error executing tool calls: {e}")
            await self.websocket_manager.send_message(session_id, {
                "type": "message",
                "role": "assistant",
                "content": f"❌ I encountered an error while processing the request: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
    
    async def _execute_script_writer_tool(self, session_id: str, args: Dict[str, Any], description: str) -> None:
        """Execute script writer tool"""
        try:
            # Execute script generation
            script_result = await self.script_writer.run(args)
            
            if script_result and "script_text" in script_result:
                script_content = script_result.get("script_text", "")
                
                # Send tool result message
                await self.websocket_manager.send_message(session_id, {
                    "type": "tool_result",
                    "tool": "script_writer",
                    "success": True,
                    "result": script_result,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Send GUI update for script
                await self.websocket_manager.send_message(session_id, {
                    "type": "gui_update",
                    "update_type": "script_created",
                    "data": {
                        "script_content": script_content
                    },
                    "timestamp": datetime.now().isoformat()
                })
                
                # Update context
                context_manager.update_session_context(session_id, {
                    "current_script": script_content,
                    "script_topic": args.get("topic", "unknown")
                })
                
            else:
                await self.websocket_manager.send_message(session_id, {
                    "type": "tool_result",
                    "tool": "script_writer",
                    "success": False,
                    "error": "Script generation failed - no script text returned",
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Script writer tool failed: {e}")
            await self.websocket_manager.send_message(session_id, {
                "type": "tool_result",
                "tool": "script_writer",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    async def _execute_broll_finder_tool(self, session_id: str, args: Dict[str, Any], description: str) -> None:
        """Execute b-roll finder tool"""
        try:
            # Execute b-roll search
            broll_result = await self.broll_finder.run(args)
            
            await self.websocket_manager.send_message(session_id, {
                "type": "tool_result",
                "tool": "broll_finder",
                "success": True,
                "result": broll_result,
                "timestamp": datetime.now().isoformat()
            })
            
            # Send GUI update for media
            if broll_result.get("downloaded_files"):
                await self.websocket_manager.send_message(session_id, {
                    "type": "gui_update",
                    "update_type": "media_downloaded",
                    "data": {
                        "media_files": broll_result.get("downloaded_files", [])
                    },
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            logger.error(f"B-roll finder tool failed: {e}")
            await self.websocket_manager.send_message(session_id, {
                "type": "tool_result",
                "tool": "broll_finder",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    async def _execute_voiceover_generator_tool(self, session_id: str, args: Dict[str, Any], description: str) -> None:
        """Execute voiceover generator tool"""
        try:
            # Execute voiceover generation
            voiceover_result = await self.voiceover_generator.run(args)
            
            await self.websocket_manager.send_message(session_id, {
                "type": "tool_result",
                "tool": "voiceover_generator",
                "success": True,
                "result": voiceover_result,
                "timestamp": datetime.now().isoformat()
            })
            
            # Send GUI update for voiceover
            if voiceover_result.get("voiceover_file"):
                await self.websocket_manager.send_message(session_id, {
                    "type": "gui_update",
                    "update_type": "voiceover_created",
                    "data": {
                        "voiceover_file": voiceover_result.get("voiceover_file")
                    },
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Voiceover generator tool failed: {e}")
            await self.websocket_manager.send_message(session_id, {
                "type": "tool_result",
                "tool": "voiceover_generator",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    async def _execute_video_processor_tool(self, session_id: str, args: Dict[str, Any], description: str) -> None:
        """Execute video processor tool"""
        try:
            # Execute video processing
            video_result = await self.video_processor.run(args)
            
            await self.websocket_manager.send_message(session_id, {
                "type": "tool_result",
                "tool": "video_processor",
                "success": True,
                "result": video_result,
                "timestamp": datetime.now().isoformat()
            })
            
            # Send GUI update for video
            if video_result.get("final_video"):
                await self.websocket_manager.send_message(session_id, {
                    "type": "gui_update",
                    "update_type": "video_created",
                    "data": {
                        "final_video": video_result.get("final_video"),
                        "thumbnail": video_result.get("thumbnail")
                    },
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Video processor tool failed: {e}")
            await self.websocket_manager.send_message(session_id, {
                "type": "tool_result",
                "tool": "video_processor",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    def _get_tool_descriptions(self) -> str:
        """Get tool descriptions for context"""
        from ..tools.mcp_protocol import mcp_protocol
        return mcp_protocol.format_tools_for_llm()
    
    async def _get_or_create_orchestrator(self, session_id: str, agent: AIAgent) -> VideoEditingOrchestrator:
        """Get or create orchestrator for a session"""
        if session_id not in self.orchestrators:
            self.orchestrators[session_id] = VideoEditingOrchestrator(agent, self.websocket_manager)
            logger.info(f"Created orchestrator for session {session_id}")
        
        return self.orchestrators[session_id]
    
    async def _get_or_create_agent(self, session_id: str, user_id: str, project_id: str = None) -> AIAgent:
        """Get or create AI agent for a session"""
        if session_id not in self.agents:
            self.agents[session_id] = self.agent_factory.create_agent(session_id, user_id, project_id)
            logger.info(f"Created AI agent for session {session_id}")
        
        return self.agents[session_id]
    
    async def _sync_with_frontend_state(self, agent: AIAgent, session_id: str) -> None:
        """Sync agent context with frontend state if available"""
        # This is a placeholder for future frontend state synchronization
        # For now, we'll keep the existing context management
        pass
    
    async def _send_ai_response(self, session_id: str, message: str) -> None:
        """Send AI response with enhanced formatting"""
        
        # Send the complete message at once for better UX
        await self._send_unique_message(session_id, {
            "type": "ai_response",
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    async def _get_ai_response(self, prompt: str, session_id: str) -> str:
        """Get AI response using the existing AI agent"""
        try:
            # Get or create agent for this session
            agent = await self._get_or_create_agent(session_id, "default", None)
            
            # Use the agent to process the prompt
            response = await agent.process_message(prompt)
            
            # Extract the response text
            if hasattr(response, 'message'):
                response_text = response.message
            else:
                response_text = str(response)
            
            # If the response is JSON, extract the user_message field
            if response_text.strip().startswith('```json'):
                try:
                    # Remove the ```json and ``` markers
                    json_text = response_text.replace('```json', '').replace('```', '').strip()
                    json_data = json.loads(json_text)
                    
                    # Extract the user_message field
                    if 'user_message' in json_data:
                        return json_data['user_message']
                    else:
                        return response_text
                except json.JSONDecodeError:
                    return response_text
            else:
                return response_text
            
        except Exception as e:
            logger.error(f"Error getting AI response: {e}")
            return "I'm having trouble processing that right now. Could you try rephrasing your request?"
    
    async def _handle_actions(self, session_id: str, actions: List[Any], agent: AIAgent) -> None:
        """Handle AI agent actions with enhanced streaming communication"""
        
        for action in actions:
            try:
                # Stream action execution with detailed progress
                await self.streaming_manager.stream_action_execution(
                    session_id, 
                    action.action_type, 
                    action.description
                )
                
                # Execute action
                result = await self._execute_action(action, agent)
                
                # Send action result
                await self._send_action_result(session_id, action)
                
                # Send GUI updates
                await self._send_action_gui_updates(session_id, action, result)
                
                # Add delay before next action
                await asyncio.sleep(2)
                
                # Send contextual suggestions
                context = {
                    "completed_actions": [action.action_type],
                    "current_project": agent.context.current_project
                }
                await self.streaming_manager.send_contextual_suggestion(session_id, context)
                
            except Exception as e:
                logger.error(f"Error executing action {action.action_type}: {e}")
                await self._send_action_error(session_id, action, str(e))
    
    async def _execute_action(self, action: Any, agent: AIAgent) -> Any:
        """Execute an action using the AI agent"""
        try:
            # Use the AI agent's action execution system
            executed_actions = await agent._execute_actions([action])
            if executed_actions and len(executed_actions) > 0:
                executed_action = executed_actions[0]
                action.status = executed_action.status
                action.result = executed_action.result
                action.error = executed_action.error
                result = executed_action.result
            else:
                result = None
            return result
        except Exception as e:
            logger.error(f"Error executing action: {e}")
            action.status = "failed"
            action.error = str(e)
            return None
    
    async def _send_action_result(self, session_id: str, action: Any) -> None:
        """Send action result with enhanced formatting"""
        
        # Convert AgentAction to serializable dict
        action_dict = {
            "action_type": action.action_type,
            "description": action.description,
            "status": "completed",
            "timestamp": datetime.now().isoformat()
        }
        
        # Add result if available
        if hasattr(action, 'result') and action.result:
            if isinstance(action.result, dict):
                action_dict["result"] = action.result
            else:
                action_dict["result"] = str(action.result)
        
        await self._send_unique_message(session_id, {
            "type": "action_result",
            "action": action_dict,
            "timestamp": datetime.now().isoformat()
        })
    
    async def _send_action_gui_updates(self, session_id: str, action: Any, result: Dict[str, Any]) -> None:
        """Send GUI updates for action completion - ensure content appears in frontend"""
        
        # Handle different action types with proper GUI updates
        if action.action_type.lower() == "create_script":
            if result and "script_text" in result:
                # Update script panel
                await self._send_unique_message(session_id, {
                    "type": "gui_update",
                    "update_type": "script_created",
                    "script_content": result["script_text"],
                    "script_file": result.get("file_path", ""),
                    "timestamp": datetime.now().isoformat()
                })
                
                # Also send to script tab specifically
                await self._send_unique_message(session_id, {
                    "type": "script_update",
                    "content": result["script_text"],
                    "file_path": result.get("file_path", ""),
                    "timestamp": datetime.now().isoformat()
                })
        
        elif action.action_type.lower() == "find_media":
            if result and "downloaded_files" in result:
                # Update project files panel
                await self._send_unique_message(session_id, {
                    "type": "gui_update",
                    "update_type": "media_found",
                    "media_files": result["downloaded_files"],
                    "file_count": len(result["downloaded_files"]),
                    "timestamp": datetime.now().isoformat()
                })
                
                # Also send to project files tab specifically
                await self._send_unique_message(session_id, {
                    "type": "project_files_update",
                    "files": result["downloaded_files"],
                    "count": len(result["downloaded_files"]),
                    "timestamp": datetime.now().isoformat()
                })
        
        elif action.action_type.lower() == "generate_voiceover":
            if result and "voiceover_path" in result:
                # Update voiceover panel
                await self._send_unique_message(session_id, {
                    "type": "gui_update",
                    "update_type": "voiceover_created",
                    "voiceover_path": result["voiceover_path"],
                    "timestamp": datetime.now().isoformat()
                })
                
                # Also send to voices tab specifically
                await self._send_unique_message(session_id, {
                    "type": "voiceover_update",
                    "file_path": result["voiceover_path"],
                    "timestamp": datetime.now().isoformat()
                })
        
        elif action.action_type.lower() == "process_video":
            if result and "video_path" in result:
                # Update video preview panel
                await self._send_unique_message(session_id, {
                    "type": "gui_update",
                    "update_type": "video_processed",
                    "video_path": result["video_path"],
                    "timestamp": datetime.now().isoformat()
                })
                
                # Also send to video preview specifically
                await self._send_unique_message(session_id, {
                    "type": "video_preview_update",
                    "video_path": result["video_path"],
                    "video_url": result.get("video_url", ""),
                    "timestamp": datetime.now().isoformat()
                })
    
    async def _send_workflow_completion_updates(self, session_id: str, project_id: str, workflow_result: Dict[str, Any]) -> None:
        """Send comprehensive GUI updates when workflow completes"""
        
        # Update all panels with final results
        if workflow_result.get("script"):
            await self._send_unique_message(session_id, {
                "type": "script_final_update",
                "content": workflow_result["script"],
                "timestamp": datetime.now().isoformat()
            })
        
        if workflow_result.get("media_files"):
            await self._send_unique_message(session_id, {
                "type": "project_files_final_update",
                "files": workflow_result["media_files"],
                "timestamp": datetime.now().isoformat()
            })
        
        if workflow_result.get("final_video"):
            await self._send_unique_message(session_id, {
                "type": "video_preview_final_update",
                "video_path": workflow_result["final_video"],
                "timestamp": datetime.now().isoformat()
            })
        
        # Send completion notification
        await self._send_unique_message(session_id, {
            "type": "workflow_completion_notification",
            "message": "🎉 All content has been generated and is now available in your project!",
            "project_id": project_id,
            "timestamp": datetime.now().isoformat()
        })
    
    async def _send_action_error(self, session_id: str, action: Any, error: str) -> None:
        """Send action error message"""
        
        await self._send_unique_message(session_id, {
            "type": "action_error",
            "action_type": action.action_type,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
    
    async def _send_error_message(self, session_id: str, error: str) -> None:
        """Send error message to frontend"""
        
        await self._send_unique_message(session_id, {
            "type": "error",
            "message": f"❌ Error: {error}",
            "timestamp": datetime.now().isoformat()
        })
    
    async def _send_unique_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """Send message to frontend, preventing duplicates"""
        # Create unique message identifier
        message_id = f"{message.get('type', 'unknown')}_{message.get('timestamp', '')}"
        
        # Check if message was already sent
        if session_id not in self.sent_messages:
            self.sent_messages[session_id] = set()
        
        if message_id in self.sent_messages[session_id]:
            logger.debug(f"Duplicate message prevented: {message_id}")
            return
        
        # Add to sent messages
        self.sent_messages[session_id].add(message_id)
        
        # Keep only last 100 messages to prevent memory issues
        if len(self.sent_messages[session_id]) > 100:
            self.sent_messages[session_id] = set(list(self.sent_messages[session_id])[-100:])
        
        # Send message via websocket manager
        await self.websocket_manager.send_message(session_id, message)
        
        logger.debug(f"Sent message to session {session_id}: {message.get('type', 'unknown')}")

# ============================================================================
# INTEGRATION WITH EXISTING SYSTEM
# ============================================================================

class ProfessionalSclipBrain(SclipBrain):
    """Enhanced SclipBrain with professional message handling"""
    
    def __init__(self, send_message_func=None, websocket_manager=None, message_handler=None):
        super().__init__(send_message_func)
        self.websocket_manager = websocket_manager
        self.message_handler = message_handler
    
    async def start_workflow_streaming(self, user_prompt: str, session_id: str, user_context: Dict[str, Any] = None):
        """Enhanced workflow streaming with professional handling"""
        
        # Use professional message handler if available
        if self.message_handler:
            await self.message_handler.handle_message(session_id, user_prompt)
            # Yield a completion message to satisfy the async for loop
            yield {
                "type": "completion",
                "message": "Processing complete",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
            return
        
        # Fall back to original implementation
        async for message in super().start_workflow_streaming(user_prompt, session_id, user_context):
            yield message
    
    async def generate_response(self, prompt: str) -> str:
        """Generate AI response - delegate to parent class"""
        return await self._get_ai_response(prompt)
    
    async def _get_ai_response(self, prompt: str) -> str:
        """Get AI response from parent class"""
        try:
            # Use the parent class's AI response method
            return await super()._get_ai_response(prompt)
        except Exception as e:
            # Fallback to a simple response if AI service fails
            return f"I understand you said: {prompt}. I'm here to help you create videos. What would you like to work on?"

# ============================================================================
# USAGE EXAMPLE
# ============================================================================

async def setup_professional_system(websocket_manager, ai_service):
    """Setup professional AI system"""
    
    # Create professional SclipBrain
    brain = ProfessionalSclipBrain(
        send_message_func=lambda msg: websocket_manager.broadcast_to_session(
            "session_id", msg
        ),
        websocket_manager=websocket_manager
    )
    
    return brain

# Example usage in main.py
"""
# In your main.py, replace the existing SclipBrain with:

from app.core.professional_handler import ProfessionalSclipBrain

# In handle_user_message function:
brain = ProfessionalSclipBrain(
    send_message_func=send_message_wrapper,
    websocket_manager=manager
)

# The brain will now use professional message handling
""" 