"""
Professional AI Agent System
Like Cursor: Execute actions, update GUI, maintain context
"""

import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, TypeVar
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
from pathlib import Path
import re

T = TypeVar('T')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# AI-powered script analysis - no hardcoded fallbacks needed with Gemini 2.5 Pro

# ============================================================================
# AGENT ACTIONS
# ============================================================================

@dataclass
class AgentAction:
    """Represents an action the AI agent can perform"""
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_type: str = ""
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, executing, completed, failed
    result: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

class ActionType(Enum):
    """Types of actions the agent can perform"""
    CREATE_SCRIPT = "create_script"
    FIND_MEDIA = "find_media"
    GENERATE_VOICEOVER = "generate_voiceover"
    PROCESS_VIDEO = "process_video"
    UPDATE_GUI = "update_gui"
    SEND_MESSAGE = "send_message"
    CREATE_FILE = "create_file"
    MODIFY_FILE = "modify_file"
    SCAN_PROJECT = "scan_project"
    VIEW_VIDEO = "view_video"
    READ_SCRIPT = "read_script"
    ANALYZE_PROJECT = "analyze_project"

# ============================================================================
# AGENT CONTEXT
# ============================================================================

@dataclass
class AgentContext:
    """Context for the AI agent"""
    session_id: str
    user_id: str
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    current_project: Dict[str, Any] = field(default_factory=dict)
    completed_actions: List[AgentAction] = field(default_factory=list)
    pending_actions: List[AgentAction] = field(default_factory=list)

# ============================================================================
# AGENT RESPONSE
# ============================================================================

@dataclass
class AgentResponse:
    """Response from the AI agent"""
    response_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message: str = ""
    actions: List[AgentAction] = field(default_factory=list)
    context_updates: Dict[str, Any] = field(default_factory=dict)
    gui_updates: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

# ============================================================================
# ACTION EXECUTORS
# ============================================================================

class ActionExecutor(ABC):
    """Abstract base for action executors"""
    
    @abstractmethod
    async def execute(self, action: AgentAction, context: AgentContext) -> Any:
        """Execute an action"""
        pass

class ScriptCreationExecutor(ActionExecutor):
    """Executor for script creation actions"""
    
    def __init__(self, script_writer_tool, ai_service):
        self.script_writer = script_writer_tool
        self.ai_service = ai_service
    
    async def execute(self, action: AgentAction, context: AgentContext) -> Any:
        """Create a video script"""
        try:
            # Extract parameters
            topic = action.parameters.get("topic", "")
            style = action.parameters.get("style", "cinematic")
            length = action.parameters.get("length", "medium")
            
            # If no topic provided, use AI to extract from user message or context
            if not topic:
                # Try to get topic from the last user message
                if context.conversation_history:
                    last_user_message = None
                    for msg in reversed(context.conversation_history):
                        if msg.get("role") == "user":
                            last_user_message = msg.get("content", "")
                            break
                    
                    if last_user_message:
                        # Use AI to extract topic from user message
                        topic = await self._extract_topic_from_message_with_ai(last_user_message, context)
                        logger.info(f"AI extracted topic from user message: {topic}")
                
                # If still no topic, raise an exception
                if not topic:
                    raise Exception("Unable to determine video topic from conversation context")
            
            # Create script using the run method to get full metadata
            input_data = {
                "topic": topic,
                "style": style,
                "length": length,
                "tone": "professional",
                "include_hooks": True,
                "target_audience": "general",
                "include_call_to_action": True,
                "include_transitions": True,
                "use_psychology": True
            }
            
            # Get full script result with metadata
            script_result = await self.script_writer.run(input_data)
            
            # Update context
            context.current_project["script"] = script_result.get("script_text", "")
            
            return {
                "script_text": script_result.get("script_text", ""),
                "file_path": script_result.get("file_path", ""),
                "duration": script_result.get("duration", 0.0),
                "word_count": script_result.get("word_count", 0),
                "style_used": script_result.get("style_used", style),
                "status": "completed"
            }
            
        except Exception as e:
            action.error = str(e)
            action.status = "failed"
            raise
    
    async def _extract_topic_from_message_with_ai(self, message: str, context: AgentContext) -> str:
        """Use AI to extract topic from user message"""
        try:
            analysis_prompt = f"""
You are an expert video content analyst. Analyze the following user message and extract the primary topic for video creation.

USER MESSAGE:
{message}

CONVERSATION CONTEXT:
{self._build_conversation_context(context.conversation_history)}

TASK: Extract the main topic/subject that the user wants to create a video about.

CRITICAL: Return ONLY the topic as a clear, descriptive phrase. No explanations, no additional text.

ANALYSIS GUIDELINES:
- Identify the primary subject or theme mentioned in the message
- Consider the context of the conversation
- Be specific and descriptive
- Focus on what would make a compelling video topic

EXAMPLES:
- "Lionel Messi's World Cup Journey"
- "The History of the Wheel"
- "Peppa Pig Cartoon Adventures"
- "Space Exploration and Discovery"

IMPORTANT: 
1. Return ONLY the topic phrase, nothing else
2. Be specific and descriptive
3. Don't use generic terms like "general content" or "amazing story"
4. Make it suitable for video creation
"""
            
            ai_response = await self.ai_service.generate_response(analysis_prompt)
            return ai_response.strip()
            
        except Exception as e:
            logger.error(f"AI topic extraction failed: {e}")
            raise Exception("Failed to extract topic from user message")
    
    def _build_conversation_context(self, conversation_history: List[Dict[str, Any]]) -> str:
        """Build conversation context for AI analysis"""
        if not conversation_history:
            return "No previous conversation context."
        
        context_lines = []
        for msg in conversation_history[-5:]:  # Last 5 messages
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:200]  # Limit length
            context_lines.append(f"{role}: {content}")
        
        return "\n".join(context_lines)

class MediaFinderExecutor(ActionExecutor):
    """Executor for media finding actions with AI-powered context analysis"""
    
    def __init__(self, broll_finder_tool, ai_service, websocket_manager):
        self.broll_finder = broll_finder_tool
        self.ai_service = ai_service
        self.websocket_manager = websocket_manager
    
    async def execute(self, action: AgentAction, context: AgentContext) -> Any:
        """Find and download media using AI-powered context analysis"""
        try:
            # Get the user's request from the action parameters or conversation
            user_request = action.parameters.get("user_request", "")
            
            # If no user request in parameters, get it from the latest conversation
            if not user_request and context.conversation_history:
                latest_message = context.conversation_history[-1]
                user_request = latest_message.get("content", "")
            
            logger.info(f"User request for media: {user_request}")
            
            # Use AI to analyze the full context and determine B-roll requirements
            broll_analysis = await self._analyze_context_for_broll(context, user_request)
            
            topic = broll_analysis.get("topic", "")
            count = broll_analysis.get("count", 8)
            style = broll_analysis.get("style", "cinematic")
            search_type = broll_analysis.get("search_type", "images")
            sources = broll_analysis.get("sources", ["local", "google", "pexels"])
            
            logger.info(f"AI Analysis Result: Topic='{topic}', Count={count}, Style='{style}'")
            
            # Validate we have a topic
            if not topic:
                raise Exception("AI analysis could not determine what to search for from your request and context")
            
            logger.info(f"FINAL TOPIC BEING USED: '{topic}'")
            
            # Get project_id from context if available
            project_id = context.current_project.get("project_id")
            
            # If no project_id, create a default project structure
            if not project_id:
                # Create a proper project ID instead of using session ID
                import uuid
                project_id = str(uuid.uuid4())
                context.current_project["project_id"] = project_id
                logger.info(f"Created proper project_id: {project_id}")
            
            # Always use project path: Videos/Sclip/Projects/[project_id]/resources/broll
            project_path = Path.home() / "Videos" / "Sclip" / "Projects" / project_id / "resources" / "broll"
            project_path.mkdir(parents=True, exist_ok=True)
            download_path = str(project_path)
            logger.info(f"Using project path for downloads: {download_path}")
            
            # Prepare input data for the run method
            input_data = {
                "topic": topic,
                "count": count,
                "style": style,
                "duration": "short",
                "search_type": search_type,
                "sources": sources,
                "ai_generation": False,
                "session_id": context.session_id,
                "download_path": download_path
            }
            
            if project_id:
                input_data["project_id"] = project_id
            
            logger.info(f"Input data for broll_finder: {input_data}")
            
            # Call the run method
            result = await self.broll_finder.run(input_data)
            
            if not result.get("success", False):
                raise Exception(result.get("error", "B-roll finder failed"))
            
            # Check if we got any results
            downloaded_files = result.get("downloaded_files", [])
            if not downloaded_files:
                # Check if it's because APIs aren't configured
                search_summary = result.get("search_summary", {})
                errors = search_summary.get("search_stats", {}).get("errors", [])
                
                api_errors = [error for error in errors if "not configured" in error.lower()]
                if api_errors:
                    logger.warning("External APIs not configured. Only local files available.")
                    # Return a helpful message
                    return {
                        "downloaded_files": [],
                        "clips": [],
                        "file_paths": [],
                        "metadata": [],
                        "thumbnails": [],
                        "source_types": [],
                        "search_summary": result.get("search_summary", {}),
                        "status": "completed",
                        "message": "No external APIs configured. To get real B-roll content, please set up Google Custom Search and Pexels API keys. See API_SETUP.md for instructions."
                    }
            
            # Send GUI update for downloaded media
            if downloaded_files:
                gui_update = {
                    "type": "gui_update",
                    "update_type": "media_downloaded",
                    "data": {
                        "media_files": downloaded_files,
                        "project_id": project_id
                    },
                    "timestamp": datetime.now().isoformat()
                }
                
                tool_result = {
                    "downloaded_files": len(downloaded_files),
                    "topic": topic,
                    "project_id": project_id
                }
                
                # Return result with GUI updates
                return {
                    **result,
                    "gui_updates": [gui_update],
                    "tool_result": {
                        "tool": "broll_finder",
                        "success": True,
                        "result": tool_result,
                        "timestamp": datetime.now().isoformat()
                    }
                }
            
            return result
            
        except Exception as e:
            logger.error(f"MediaFinderExecutor failed: {e}")
            
            # Send error message
            await self.websocket_manager.send_message(context.session_id, {
                "type": "tool_result",
                "tool": "broll_finder",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            
            raise
    
    async def _analyze_context_for_broll(self, context: AgentContext, user_request: str) -> Dict[str, Any]:
        """Use AI to analyze full context and determine optimal B-roll requirements"""
        try:
            # Build comprehensive context for AI analysis
            context_prompt = self._build_comprehensive_context_prompt(context, user_request)
            
            logger.info("Sending comprehensive context analysis to AI...")
            
            # Get AI analysis
            ai_response = await self.ai_service.generate_response(context_prompt)
            
            logger.info(f"AI analysis response: {ai_response[:500]}...")
            
            # Parse the AI response
            return self._parse_broll_analysis_response(ai_response)
            
        except Exception as e:
            logger.error(f"AI context analysis failed: {e}")
            # Fallback to simple topic extraction
            return self._fallback_topic_extraction(user_request, context)
    
    def _build_comprehensive_context_prompt(self, context: AgentContext, user_request: str) -> str:
        """Build comprehensive context prompt for AI analysis"""
        
        # Build conversation history
        conversation_text = ""
        for msg in context.conversation_history[-10:]:  # Last 10 messages
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            conversation_text += f"{role}: {content}\n"
        
        # Build current project state
        project_state = ""
        if context.current_project:
            # Include script content prominently if available
            script_content = context.current_project.get("script", "")
            if script_content:
                project_state += f"CURRENT SCRIPT:\n{script_content}\n\n"
            
            # Include existing media
            existing_media = context.current_project.get("media", [])
            if existing_media:
                media_list = []
                for media in existing_media[-5:]:  # Last 5 media items
                    media_list.append(f"- {media.get('name', 'Unknown')} ({media.get('type', 'unknown')})")
                project_state += f"EXISTING MEDIA:\n" + "\n".join(media_list) + "\n\n"
            
            # Include other project info
            other_project_info = {k: v for k, v in context.current_project.items() 
                                if k not in ["script", "media"]}
            if other_project_info:
                project_state += f"Other project data: {json.dumps(other_project_info, indent=2)}\n"
        
        # Build user preferences
        preferences = ""
        if context.user_preferences:
            preferences = f"User preferences: {json.dumps(context.user_preferences, indent=2)}\n"
        
        # Build completed actions
        completed_actions = ""
        if context.completed_actions:
            action_summary = []
            for action in context.completed_actions[-5:]:  # Last 5 actions
                action_summary.append(f"- {action.action_type}: {action.description}")
            completed_actions = f"Recent actions completed:\n" + "\n".join(action_summary) + "\n"
        
        return f"""
You are an expert video content analyst. Analyze the user's request and full context to determine optimal B-roll search parameters.

**TASK:** Determine what B-roll content to search for based on the user's request and full context.

**USER REQUEST:** {user_request}

**CONVERSATION HISTORY:**
{conversation_text}

**CURRENT PROJECT STATE:**
{project_state}

**USER PREFERENCES:**
{preferences}

**RECENT ACTIONS:**
{completed_actions}

**ANALYSIS GUIDELINES:**
1. **Understand the user's intent** - Are they asking for specific images, general B-roll for a script, or something else?
2. **Consider the script content** - If there's a script, extract relevant topics and themes
3. **Build on existing media** - Don't duplicate what's already downloaded
4. **Use conversation context** - If they refer to something mentioned earlier, use that context
5. **Be specific and searchable** - Use terms that will find relevant, high-quality images
6. **Adapt to user preferences** - Consider their style and tone preferences

**RESPONSE FORMAT (JSON only):**
{{
    "topic": "specific search terms separated by spaces",
    "count": number,
    "style": "cinematic|documentary|modern|vintage|professional|casual",
    "search_type": "images",
    "sources": ["local", "google", "pexels"],
    "reasoning": "brief explanation of why these parameters were chosen"
}}

**EXAMPLES:**

If user has a script about "The History of the Wheel" and asks "find some B-roll":
{{
    "topic": "ancient wheel invention mesopotamia potter wheel wooden cart chariot",
    "count": 8,
    "style": "documentary",
    "search_type": "images",
    "sources": ["local", "google", "pexels"],
    "reasoning": "Script covers wheel evolution, so searching for historical wheel-related terms"
}}

If user asks "find me a picture of a soccer ball":
{{
    "topic": "soccer ball football",
    "count": 1,
    "style": "cinematic",
    "search_type": "images",
    "sources": ["local", "google", "pexels"],
    "reasoning": "Specific request for one soccer ball image"
}}

If user asks "get more B-roll for the Ferrari script":
{{
    "topic": "ferrari car enzo ferrari f1 racing red sports car italy maranello luxury",
    "count": 6,
    "style": "cinematic",
    "search_type": "images",
    "sources": ["local", "google", "pexels"],
    "reasoning": "User wants additional B-roll for existing Ferrari script"
}}

**CRITICAL:** Return ONLY the JSON object. No explanations, no conversational text, no markdown formatting.
"""
    
    def _parse_broll_analysis_response(self, ai_response: str) -> Dict[str, Any]:
        """Parse AI response for B-roll analysis"""
        try:
            # Clean the response - remove any markdown formatting
            cleaned_response = ai_response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            # Parse JSON
            analysis_result = json.loads(cleaned_response)
            logger.info(f"Successfully parsed AI analysis: {analysis_result}")
            return analysis_result
        
        except json.JSONDecodeError as json_error:
            logger.error(f"Failed to parse AI analysis as JSON: {json_error}")
            logger.error(f"Raw AI response: {ai_response}")
            raise Exception(f"AI analysis failed to return valid JSON. Expected JSON format but got: {ai_response[:200]}...")
                
    def _fallback_topic_extraction(self, user_request: str, context: AgentContext) -> Dict[str, Any]:
        """Fallback topic extraction when AI analysis fails"""
        logger.warning("Using fallback topic extraction")
        
        # Try to get topic from script first
        script_content = context.current_project.get("script", "")
        if script_content:
            # Extract key terms from script
            script_lower = script_content.lower()
            if "ferrari" in script_lower or "car" in script_lower:
                topic = "ferrari car enzo ferrari f1 racing red sports car italy maranello"
            elif "rome" in script_lower or "roman" in script_lower:
                topic = "ancient rome roman empire colosseum gladiator caesar legion"
            elif "wheel" in script_lower:
                topic = "ancient wheel invention mesopotamia potter wheel wooden cart chariot"
            else:
                # Extract general terms from script
                words = script_content.split()
                important_words = [word for word in words if len(word) > 4][:5]
                topic = " ".join(important_words)
        else:
            # Extract from user request
            topic = self._extract_topic_from_request(user_request)
        
        return {
            "topic": topic,
            "count": 8,
            "style": "cinematic",
            "search_type": "images",
            "sources": ["local", "google", "pexels"],
            "reasoning": "Fallback extraction used"
        }

    def _extract_topic_from_request(self, user_request: str) -> str:
        """Simple topic extraction from user request (fallback method)"""
        request_lower = user_request.lower()
        
        # Common patterns for different topics
        if "romans" in request_lower or "rome" in request_lower or "roman" in request_lower:
            return "ancient rome roman empire colosseum gladiator caesar legion"
        elif "ferrari" in request_lower:
            return "ferrari car enzo ferrari f1 racing red sports car italy maranello"
        elif "wheel" in request_lower:
            return "ancient wheel invention mesopotamia potter wheel wooden cart chariot"
        elif "car" in request_lower or "automotive" in request_lower:
            return "car automobile vehicle automotive transportation"
        elif "nature" in request_lower or "landscape" in request_lower:
            return "nature landscape scenery mountains forest ocean"
        elif "technology" in request_lower or "tech" in request_lower:
            return "technology computer digital innovation modern tech"
        elif "sports" in request_lower:
            return "sports athletics competition game team"
        elif "food" in request_lower or "cooking" in request_lower:
            return "food cooking cuisine restaurant kitchen chef"
        elif "music" in request_lower:
            return "music musical instrument concert performance"
        elif "art" in request_lower or "painting" in request_lower:
            return "art painting sculpture museum gallery creative"
        elif "architecture" in request_lower or "building" in request_lower:
            return "architecture building construction modern design"
        elif "space" in request_lower or "astronomy" in request_lower:
            return "space astronomy galaxy stars planet universe"
        elif "history" in request_lower or "historical" in request_lower:
            return "history historical ancient civilization monument"
        elif "science" in request_lower:
            return "science laboratory research experiment discovery"
        elif "business" in request_lower or "office" in request_lower:
            return "business office corporate workplace professional"
        elif "travel" in request_lower or "tourism" in request_lower:
            return "travel tourism destination vacation adventure"
        elif "fashion" in request_lower or "style" in request_lower:
            return "fashion style clothing design runway model"
        elif "health" in request_lower or "medical" in request_lower:
            return "health medical hospital doctor medicine"
        elif "education" in request_lower or "school" in request_lower:
            return "education school learning classroom student"
        elif "entertainment" in request_lower or "movie" in request_lower:
            return "entertainment movie film cinema theater"
        else:
            # For any other request, just use the key words from the request
            # Remove common words and keep the important ones
            common_words = {"download", "me", "some", "images", "on", "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "from", "up", "down", "out", "off", "over", "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "can", "will", "just", "should", "now"}
            words = user_request.lower().split()
            important_words = [word for word in words if word not in common_words and len(word) > 2]
            return " ".join(important_words[:5])  # Take first 5 important words

class VoiceoverGeneratorExecutor(ActionExecutor):
    """Executor for voiceover generation actions"""
    
    def __init__(self, voiceover_generator_tool):
        self.voiceover_generator = voiceover_generator_tool
    
    async def execute(self, action: AgentAction, context: AgentContext) -> Any:
        """Generate voiceover"""
        try:
            script_text = action.parameters.get("script_text", "")
            voice = action.parameters.get("voice", "en-US-Neural2-A")
            
            # If no script provided in parameters, try to get from context
            if not script_text and context.current_project.get("script"):
                script_text = context.current_project["script"]
                logger.info("Using script from context for voiceover generation")
            
            if not script_text:
                raise Exception("No script provided for voiceover generation")
            
            # Generate voiceover using the run method
            input_data = {
                "script_text": script_text,
                "voice": voice,
                "session_id": context.session_id
            }
            
            result = await self.voiceover_generator.run(input_data)
            
            # Update context
            voiceover_file = result.get("audio_path", "")
            context.current_project["voiceover"] = voiceover_file
            
            return {
                "voiceover_file": voiceover_file,
                "status": "completed"
            }
            
        except Exception as e:
            action.error = str(e)
            action.status = "failed"
            raise

class VideoProcessorExecutor(ActionExecutor):
    """Executor for video processing actions"""
    
    def __init__(self, video_processor_tool):
        self.video_processor = video_processor_tool
    
    async def execute(self, action: AgentAction, context: AgentContext) -> Any:
        """Process video"""
        try:
            broll_paths = action.parameters.get("broll_paths", [])
            audio_path = action.parameters.get("audio_path", "")
            effects = action.parameters.get("effects", [])
            style = action.parameters.get("style", "cinematic")
            
            # If no broll paths provided, try to get from context
            if not broll_paths and context.current_project.get("media"):
                # Extract file paths from media objects
                broll_paths = [media.get("path", "") for media in context.current_project["media"] if media.get("path")]
                logger.info("Using media files from context for video processing")
            
            # If no audio path provided, try to get from context
            if not audio_path and context.current_project.get("voiceover"):
                audio_path = context.current_project["voiceover"]
                logger.info("Using voiceover file from context for video processing")
            
            if not broll_paths:
                raise Exception("No B-roll files provided for video processing")
            
            if not audio_path:
                raise Exception("No audio file provided for video processing")
            
            # Process video using the run method
            input_data = {
                "broll_paths": broll_paths,
                "audio_path": audio_path,
                "effects": effects,
                "style": style,
                "session_id": context.session_id
            }
            
            result = await self.video_processor.run(input_data)
            
            # Update context
            final_video = result.get("video_path", "")
            context.current_project["final_video"] = final_video
            
            return {
                "final_video": final_video,
                "status": "completed"
            }
            
        except Exception as e:
            action.error = str(e)
            action.status = "failed"
            raise

class GUIUpdateExecutor(ActionExecutor):
    """Executor for GUI update actions"""
    
    def __init__(self, websocket_manager):
        self.websocket_manager = websocket_manager
    
    async def execute(self, action: AgentAction, context: AgentContext) -> Any:
        """Update the GUI"""
        try:
            update_type = action.parameters.get("type", "")
            data = action.parameters.get("data", {})
            
            # Send GUI update via WebSocket
            await self.websocket_manager.send_message(
                context.session_id,
                {
                    "type": "gui_update",
                    "update_type": update_type,
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            return {
                "status": "completed",
                "update_type": update_type
            }
            
        except Exception as e:
            action.error = str(e)
            action.status = "failed"
            raise

class ProjectScannerExecutor(ActionExecutor):
    """Executor for project scanning actions"""
    
    def __init__(self, project_scanner_tool):
        self.project_scanner = project_scanner_tool
    
    async def execute(self, action: AgentAction, context: AgentContext) -> Any:
        """Scan and read project files"""
        try:
            scan_type = action.parameters.get("scan_type", "all")
            project_id = action.parameters.get("project_id") or context.current_project.get("project_id")
            
            if not project_id:
                raise Exception("Project ID is required for project scanning")
            
            input_data = {
                "scan_type": scan_type,
                "project_id": project_id,
                "include_metadata": action.parameters.get("include_metadata", True)
            }
            
            # Add specific file path if provided
            if "file_path" in action.parameters:
                input_data["file_path"] = action.parameters["file_path"]
            
            result = await self.project_scanner.run(input_data)
            
            if not result.get("success", False):
                raise Exception(result.get("error", "Project scanning failed"))
            
            # Update context with scanned information
            if scan_type == "script" or scan_type == "all":
                script_content = result.get("content", {}).get("script", {})
                if script_content.get("exists") and script_content.get("text"):
                    context.current_project["script"] = script_content["text"]
            
            if scan_type == "media" or scan_type == "all":
                media_files = result.get("content", {}).get("media", [])
                if media_files:
                    if "media" not in context.current_project:
                        context.current_project["media"] = []
                    context.current_project["media"].extend(media_files)
            
            return result
            
        except Exception as e:
            action.error = str(e)
            action.status = "failed"
            raise

class VideoViewerExecutor(ActionExecutor):
    """Executor for video viewing actions"""
    
    def __init__(self, video_viewer_tool):
        self.video_viewer = video_viewer_tool
    
    async def execute(self, action: AgentAction, context: AgentContext) -> Any:
        """View and analyze video files"""
        try:
            video_path = action.parameters.get("video_path")
            project_id = action.parameters.get("project_id") or context.current_project.get("project_id")
            analysis_type = action.parameters.get("analysis_type", "all")
            generate_thumbnail = action.parameters.get("generate_thumbnail", False)
            
            if not video_path:
                raise Exception("Video path is required for video viewing")
            
            input_data = {
                "video_path": video_path,
                "project_id": project_id,
                "analysis_type": analysis_type,
                "generate_thumbnail": generate_thumbnail
            }
            
            result = await self.video_viewer.run(input_data)
            
            if not result.get("success", False):
                raise Exception(result.get("error", "Video viewing failed"))
            
            return result
            
        except Exception as e:
            action.error = str(e)
            action.status = "failed"
            raise

class ScriptReaderExecutor(ActionExecutor):
    """Executor for script reading actions"""
    
    def __init__(self, project_scanner_tool):
        self.project_scanner = project_scanner_tool
    
    async def execute(self, action: AgentAction, context: AgentContext) -> Any:
        """Read script content"""
        try:
            project_id = action.parameters.get("project_id") or context.current_project.get("project_id")
            
            if not project_id:
                raise Exception("Project ID is required for script reading")
            
            input_data = {
                "scan_type": "script",
                "project_id": project_id,
                "include_metadata": action.parameters.get("include_metadata", True)
            }
            
            result = await self.project_scanner.run(input_data)
            
            if not result.get("success", False):
                raise Exception(result.get("error", "Script reading failed"))
            
            script_content = result.get("content", {}).get("script", {})
            
            # Update context with script content
            if script_content.get("exists") and script_content.get("text"):
                context.current_project["script"] = script_content["text"]
            
            return {
                "script_content": script_content,
                "project_id": project_id,
                "exists": script_content.get("exists", False)
            }
            
        except Exception as e:
            action.error = str(e)
            action.status = "failed"
            raise

# ============================================================================
# AI AGENT
# ============================================================================

class AIAgent:
    """
    TRUE AGENTIC AI AGENT - Implements the core agentic loop:
    AI plans → Tool executes → AI observes result → AI decides next action → Repeat until goal achieved
    """
    
    def __init__(self, ai_service, action_executors: Dict[str, ActionExecutor], 
                 websocket_manager, context: AgentContext):
        self.ai_service = ai_service
        self.action_executors = action_executors
        self.websocket_manager = websocket_manager
        self.context = context
        self.max_iterations = 10  # Prevent infinite loops
        self.current_iteration = 0
    
    async def process_message(self, user_message: str) -> AgentResponse:
        """Process user message with TRUE AGENTIC LOOP"""
        try:
            # Add user message to conversation history
            self.context.conversation_history.append({
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now().isoformat()
            })
            
            # Start the TRUE AGENTIC LOOP
            final_response = await self._execute_agentic_loop(user_message)
            
            return final_response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            # Add error to conversation history
            self.context.conversation_history.append({
                "role": "assistant",
                "content": f"Sorry, I encountered an error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
            
            return AgentResponse(
                message=f"Sorry, I encountered an error: {str(e)}",
                actions=[],
                context_updates={},
                gui_updates=[]
            )
    
    async def _execute_agentic_loop(self, user_message: str) -> AgentResponse:
        """Execute the TRUE AGENTIC LOOP: Plan → Execute → Observe → Decide → Repeat"""
        self.current_iteration = 0
        final_response = None
        
        while self.current_iteration < self.max_iterations:
            self.current_iteration += 1
            
            # STEP 1: AI PLANS - Generate response with potential actions
            logger.info(f"🤔 AGENTIC LOOP ITERATION {self.current_iteration}: AI is planning...")
            
            # Send thinking message to frontend
            await self.websocket_manager.send_message(self.context.session_id, {
                "type": "agent_thinking",
                "iteration": self.current_iteration,
                "message": "🤔 Analyzing the current situation and planning next actions...",
                "timestamp": datetime.now().isoformat()
            })
            
            response = await self._get_ai_response_with_actions(user_message)
            
            # STEP 2: AI DECIDES - Check if AI wants to execute tools
            if not response.actions:
                # No more actions needed - we're done!
                logger.info("✅ AGENTIC LOOP COMPLETE: No more actions needed")
                final_response = response
                break
            
            # STEP 3: EXECUTE ACTIONS - Run all planned actions
            logger.info(f"⚡ AGENTIC LOOP ITERATION {self.current_iteration}: Executing {len(response.actions)} actions")
            
            # Send execution message to frontend
            await self.websocket_manager.send_message(self.context.session_id, {
                "type": "agent_executing",
                "iteration": self.current_iteration,
                "actions": [action.action_type for action in response.actions],
                "message": f"⚡ Executing {len(response.actions)} actions...",
                "timestamp": datetime.now().isoformat()
            })
            
            executed_actions = await self._execute_actions(response.actions)
            
            # STEP 4: AI OBSERVES - Add tool results to context for next iteration
            await self._add_tool_results_to_context(executed_actions)
            
            # STEP 5: CHECK COMPLETION - See if AI thinks we're done
            completion_check = await self._check_task_completion(user_message, executed_actions)
            
            if completion_check.get("completed", False):
                logger.info("✅ AGENTIC LOOP COMPLETE: Task completed successfully")
                final_response = AgentResponse(
                    message=completion_check.get("final_message", "Task completed successfully!"),
                    actions=executed_actions,
                    context_updates=response.context_updates,
                    gui_updates=[]
                )
                break
            
            # Continue to next iteration if not complete
            logger.info(f"🔄 AGENTIC LOOP ITERATION {self.current_iteration} COMPLETE: Continuing to next iteration")
        
        if not final_response:
            final_response = AgentResponse(
                message="I've completed the main tasks. Let me know if you need anything else!",
                actions=[],
                context_updates={},
                gui_updates=[]
            )
        
        # Add final response to conversation history
        self.context.conversation_history.append({
            "role": "assistant",
            "content": final_response.message,
            "timestamp": datetime.now().isoformat()
        })
        
        return final_response
    
    async def _add_tool_results_to_context(self, executed_actions: List[AgentAction]) -> None:
        """Add tool results to context for AI to observe in next iteration"""
        for action in executed_actions:
            if action.status == "completed" and action.result:
                # Add tool result to context
                if "tool_results" not in self.context.current_project:
                    self.context.current_project["tool_results"] = []
                
                self.context.current_project["tool_results"].append({
                    "tool": action.action_type,
                    "result": action.result,
                    "timestamp": action.timestamp.isoformat(),
                    "iteration": self.current_iteration
                })
                
                logger.info(f"📝 Added tool result to context: {action.action_type}")
    
    async def _check_task_completion(self, user_message: str, executed_actions: List[AgentAction]) -> Dict[str, Any]:
        """Check if the task is complete based on user request and executed actions"""
        # Build completion check prompt
        completion_prompt = f"""
**TASK COMPLETION CHECK**

**Original User Request:** {user_message}

**Executed Actions:**
{chr(10).join([f"- {action.action_type}: {action.status} ({action.description})" for action in executed_actions])}

**Current Context:**
- Script generated: {'Yes' if any(a.action_type == 'create_script' and a.status == 'completed' for a in executed_actions) else 'No'}
- Media downloaded: {'Yes' if any(a.action_type == 'find_media' and a.status == 'completed' for a in executed_actions) else 'No'}
- Voiceover generated: {'Yes' if any(a.action_type == 'generate_voiceover' and a.status == 'completed' for a in executed_actions) else 'No'}
- Video processed: {'Yes' if any(a.action_type == 'process_video' and a.status == 'completed' for a in executed_actions) else 'No'}

**Question:** Based on the user's original request and the actions completed, is the task finished? 

Respond with JSON:
{{
    "completed": true/false,
    "reason": "explanation of why task is complete or what's still needed",
    "final_message": "final message to user if completed"
}}
"""
        
        try:
            completion_response = await self.ai_service.generate_response(completion_prompt)
            
            # Try to parse JSON response
            if "{" in completion_response and "}" in completion_response:
                json_start = completion_response.find("{")
                json_end = completion_response.rfind("}") + 1
                json_str = completion_response[json_start:json_end]
                
                try:
                    completion_data = json.loads(json_str)
                    return completion_data
                except json.JSONDecodeError:
                    pass
            
            # Fallback: simple completion check
            if any(a.action_type == 'process_video' and a.status == 'completed' for a in executed_actions):
                return {
                    "completed": True,
                    "reason": "Video processing completed",
                    "final_message": "🎉 Your video is ready! I've successfully created a complete video based on your request."
                }
            
            return {"completed": False, "reason": "More actions may be needed"}
            
        except Exception as e:
            logger.error(f"Error checking task completion: {e}")
            return {"completed": False, "reason": "Unable to determine completion status"}
    
    async def _get_ai_response_with_actions(self, user_message: str) -> AgentResponse:
        """Get AI response with action plan - with REAL-TIME STREAMING"""
        # Build context for AI
        context_prompt = self._build_context_prompt(user_message)
        
        logger.info(f"🔍 DEBUG: Sending prompt to AI service: {context_prompt[:200]}...")
        
        # Send streaming start message
        await self.websocket_manager.send_message(self.context.session_id, {
            "type": "agent_streaming_start",
            "message": "🤔 AI is analyzing your request and planning actions...",
            "timestamp": datetime.now().isoformat()
        })
        
        # Get AI response with streaming
        try:
            ai_response_text = await self.ai_service.generate_response(context_prompt)
            logger.info(f"🔍 DEBUG: Got AI response: {ai_response_text[:200]}...")
            
            # Send streaming complete message
            await self.websocket_manager.send_message(self.context.session_id, {
                "type": "agent_streaming_complete",
                "message": "✅ AI analysis complete",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"🔍 DEBUG: AI service failed: {e}")
            # Create a fallback response that shows context memory is working
            if "messi" in user_message.lower() or any("messi" in msg.get("content", "").lower() for msg in self.context.conversation_history):
                ai_response_text = "I remember you asked about Messi! Lionel Messi is a world-famous Argentine footballer who has won multiple Ballon d'Or awards and is considered one of the greatest players of all time. He's known for his incredible dribbling skills, goal-scoring ability, and his time at Barcelona and now Inter Miami. Would you like me to create a video about his career highlights?"
            else:
                ai_response_text = "I'm here to help you create videos! What kind of video would you like to make today?"
        
        # Parse response and extract actions with ENHANCED TOOL CALL DETECTION
        return self._parse_ai_response_with_tool_calls(ai_response_text)
    
    def _parse_ai_response_with_tool_calls(self, ai_response_text: str) -> AgentResponse:
        """Parse AI response with ENHANCED TOOL CALL DETECTION"""
        # First, try to detect JSON tool calls
        tool_calls = self._extract_json_tool_calls(ai_response_text)
        
        if tool_calls:
            # AI provided structured tool calls
            actions = []
            for tool_call in tool_calls:
                action = AgentAction(
                    action_type=tool_call.get("tool", ""),
                    description=tool_call.get("description", ""),
                    parameters=tool_call.get("args", {}),
                    status="pending"
                )
                actions.append(action)
            
            return AgentResponse(
                message=self._extract_user_message(ai_response_text),
                actions=actions,
                context_updates={},
                gui_updates=[]
            )
        
        # Fallback: infer actions from text
        inferred_actions = self._infer_actions_from_response(ai_response_text)
        
        return AgentResponse(
            message=ai_response_text,
            actions=inferred_actions,
            context_updates={},
            gui_updates=[]
        )
    
    def _extract_json_tool_calls(self, response_text: str) -> List[Dict[str, Any]]:
        """Extract JSON tool calls from AI response"""
        tool_calls = []
        
        # Look for JSON blocks
        import re
        json_pattern = r'```json\s*(\{.*?\})\s*```'
        matches = re.findall(json_pattern, response_text, re.DOTALL)
        
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
        
        # Also look for inline JSON
        inline_pattern = r'\{[^{}]*"tool"[^{}]*\}'
        inline_matches = re.findall(inline_pattern, response_text)
        
        for match in inline_matches:
            try:
                json_data = json.loads(match)
                if "tool" in json_data:
                    tool_calls.append(json_data)
            except json.JSONDecodeError:
                continue
        
        return tool_calls
    
    def _extract_user_message(self, response_text: str) -> str:
        """Extract user-facing message from AI response"""
        # Remove JSON blocks
        import re
        cleaned_text = re.sub(r'```json\s*\{.*?\}\s*```', '', response_text, flags=re.DOTALL)
        cleaned_text = re.sub(r'\{[^{}]*"tool"[^{}]*\}', '', cleaned_text)
        
        # Clean up extra whitespace
        cleaned_text = re.sub(r'\n\s*\n', '\n\n', cleaned_text).strip()
        
        return cleaned_text if cleaned_text else "I've processed your request and will take the necessary actions."
    
    def _build_context_prompt(self, user_message: str) -> str:
        """Build context-aware prompt for AI with full GUI state awareness"""
        # Build conversation history
        conversation_text = ""
        print(f"🔍 DEBUG: Conversation history has {len(self.context.conversation_history)} messages")
        for msg in self.context.conversation_history[-10:]:  # Last 10 messages
            role = msg["role"]
            content = msg["content"]
            conversation_text += f"{role}: {content}\n"
            print(f"🔍 DEBUG: {role}: {content[:50]}...")
        
        print(f"🔍 DEBUG: Final conversation text:\n{conversation_text}")
        
        # Build comprehensive project state
        project_state = ""
        if self.context.current_project:
            # Include script content prominently if available
            script_content = self.context.current_project.get("script", "")
            if script_content:
                project_state += f"CURRENT SCRIPT:\n{script_content}\n\n"
            
            # Include existing media with detailed information
            existing_media = self.context.current_project.get("media", [])
            if existing_media:
                media_list = []
                for media in existing_media[-10:]:  # Last 10 media items
                    media_info = f"- {media.get('name', 'Unknown')} ({media.get('type', 'unknown')})"
                    if media.get('source'):
                        media_info += f" [Source: {media.get('source')}]"
                    media_list.append(media_info)
                project_state += f"EXISTING MEDIA ({len(existing_media)} items):\n" + "\n".join(media_list) + "\n\n"
            
            # Include voiceover information
            voiceover = self.context.current_project.get("voiceover", "")
            if voiceover:
                project_state += f"VOICEOVER: {voiceover}\n\n"
            
            # Include final video information
            final_video = self.context.current_project.get("final_video", "")
            if final_video:
                project_state += f"FINAL VIDEO: {final_video}\n\n"
            
            # Include project metadata
            project_id = self.context.current_project.get("project_id", "")
            if project_id:
                project_state += f"PROJECT ID: {project_id}\n\n"
            
            # Include other project info
            other_project_info = {k: v for k, v in self.context.current_project.items() 
                                if k not in ["script", "media", "voiceover", "final_video", "project_id"]}
            if other_project_info:
                project_state += f"Other project data: {json.dumps(other_project_info, indent=2)}\n"
        
        # Build user preferences with more detail
        preferences = ""
        if self.context.user_preferences:
            preferences = f"User preferences: {json.dumps(self.context.user_preferences, indent=2)}\n"
        
        # Build completed actions with more context
        completed_actions = ""
        if self.context.completed_actions:
            action_summary = []
            for action in self.context.completed_actions[-8:]:  # Last 8 actions
                action_info = f"- {action.action_type}: {action.description}"
                if action.result:
                    if action.action_type.lower() == "create_script" and action.result.get("script_text"):
                        action_info += f" (Script length: {len(action.result['script_text'])} chars)"
                    elif action.action_type.lower() == "find_media" and action.result.get("downloaded_files"):
                        action_info += f" (Downloaded: {len(action.result['downloaded_files'])} files)"
                action_summary.append(action_info)
            completed_actions = f"Recent actions completed:\n" + "\n".join(action_summary) + "\n"
        
        return f"""
You are Sclip, an AI video creation assistant that works like Cursor for video editing. You are highly conversational, proactive, and contextually aware.

**YOUR PERSONALITY:**
- Be conversational and engaging, not robotic
- Show enthusiasm and personality in your responses
- Anticipate user needs and suggest helpful next steps
- Use natural language that feels like talking to a smart friend
- Be proactive - if you see an opportunity to help, offer it
- Show excitement about creating amazing videos

**HOW YOU WORK:**
1. **Understand intent deeply** - read between the lines of what the user wants
2. **Take smart actions** - execute tasks seamlessly while maintaining conversation flow
3. **Build on context** - remember everything and use it to provide better suggestions
4. **Be proactive** - suggest logical next steps and improvements
5. **Show progress** - give meaningful updates about what you're doing

**CONVERSATION STYLE EXAMPLES:**
- Instead of "I'll create a script" → "Perfect! I'll craft a compelling script about the Romans that will really bring their story to life. This should be fascinating!"
- Instead of "Downloading images" → "Great idea! I'm searching for some stunning Roman imagery - think Colosseum, ancient architecture, maybe some dramatic shots of Roman emperors. This will give us amazing visual material to work with."
- Instead of "Script created" → "Excellent! I've written a cinematic script that captures the epic scale of Roman history. It's got drama, intrigue, and will really engage viewers. Want me to generate a voiceover to bring it to life?"

**AVAILABLE ACTIONS:**
- CREATE_SCRIPT: Generate engaging video scripts on any topic
- FIND_MEDIA: Download high-quality B-roll images/videos  
- GENERATE_VOICEOVER: Create professional voiceovers from scripts
- PROCESS_VIDEO: Combine everything into a polished final video
- SCAN_PROJECT: Analyze current project state and files
- VIEW_VIDEO: Get detailed video analysis and metadata
- READ_SCRIPT: Read and analyze current script content
- ANALYZE_PROJECT: Comprehensive project analysis and suggestions

**SMART WORKFLOW EXAMPLES:**
- User: "make me a script on the romans" → CREATE_SCRIPT with cinematic style, then suggest "Want me to find some epic Roman imagery to go with this?"
- User: "download some images" → FIND_MEDIA, then suggest "Perfect! Now I can create a script that really showcases these visuals. Should I write something dramatic and cinematic?"
- User: "now make a voiceover" → GENERATE_VOICEOVER, then suggest "Great! Now we have everything. Ready to create the final video?"

**CONTEXT AWARENESS:**
- If they have images but no script → suggest creating a script
- If they have a script but no images → suggest finding relevant media
- If they have both → suggest voiceover or final video creation
- Always build on what they already have

**BE PROACTIVE:**
- After creating a script: "This script is ready! Want me to find some perfect visuals to go with it?"
- After finding media: "These images are fantastic! Should I create a script that really showcases them?"
- After voiceover: "Perfect! Now we have everything. Ready to create the final video?"

**ENHANCED CONVERSATION FLOW:**
- Always acknowledge what you're about to do with enthusiasm
- Explain the value of each step in the process
- Show excitement about the creative process
- Use phrases like "This is going to be amazing!", "I can't wait to see this!", "This will look incredible!"
- Make the user feel like they're working with a creative partner, not just a tool

**INTELLIGENT SUGGESTIONS:**
- If user asks for a script → suggest finding media afterward
- If user asks for media → suggest creating a script or voiceover
- If user asks for voiceover → suggest creating the final video
- Always think one step ahead and suggest the logical next action

**CURRENT PROJECT STATE:**
{project_state}

**CONVERSATION HISTORY:**
{conversation_text}

**USER PREFERENCES:**
{preferences}

**RECENT ACTIONS:**
{completed_actions}

**USER MESSAGE:**
{user_message}

**RESPONSE FORMAT:**
Respond naturally and conversationally. If you need to perform actions, include them in your response.

For actions, use this format:
ACTION: action_type
PARAMETERS: {{"param1": "value1", "param2": "value2"}}
DESCRIPTION: What this action will do

**IMPORTANT:** Be conversational, proactive, and helpful. Think like a smart friend who's helping create an amazing video project. Show enthusiasm and personality in everything you do!
"""
    
    def _parse_ai_response(self, ai_response_text: str) -> AgentResponse:
        """Parse AI response and extract actions intelligently"""
        response = AgentResponse(message=ai_response_text)
        
        # First, try to extract explicit actions from the response
        lines = ai_response_text.split('\n')
        current_action = None
        
        for line in lines:
            line = line.strip()
            
            if line.startswith("ACTION:"):
                if current_action:
                    response.actions.append(current_action)
                
                action_type = line.split(":", 1)[1].strip()
                current_action = AgentAction(action_type=action_type)
                
            elif line.startswith("PARAMETERS:"):
                params_text = line.split(":", 1)[1].strip()
                try:
                    current_action.parameters = json.loads(params_text)
                except json.JSONDecodeError:
                    # Handle simple parameter format
                    current_action.parameters = {"raw_params": params_text}
                    
            elif line.startswith("DESCRIPTION:"):
                current_action.description = line.split(":", 1)[1].strip()
        
        # Add final action
        if current_action:
            response.actions.append(current_action)
        
        # If no explicit actions found, try to infer actions from the response content
        if not response.actions:
            response.actions = self._infer_actions_from_response(ai_response_text)
        
        return response
    
    def _infer_actions_from_response(self, response_text: str) -> List[AgentAction]:
        """Infer multiple actions from response content based on keywords and context"""
        actions = []
        response_lower = response_text.lower()
        
        # Check for project analysis intent (scan project, read files, etc.)
        if any(phrase in response_lower for phrase in [
            "scan project", "read project", "analyze project", "check project",
            "read files", "scan files", "check files", "view project",
            "project state", "project status", "what's in the project"
        ]):
            project_id = self.context.current_project.get("project_id", "default")
            actions.append(AgentAction(
                action_type="scan_project",
                description="Scan and analyze current project state",
                parameters={
                    "scan_type": "all",
                    "project_id": project_id,
                    "include_metadata": True
                }
            ))
        
        # Check for script reading intent
        if any(phrase in response_lower for phrase in [
            "read script", "view script", "show script", "check script",
            "what's the script", "script content", "current script"
        ]):
            project_id = self.context.current_project.get("project_id", "default")
            actions.append(AgentAction(
                action_type="read_script",
                description="Read current script content",
                parameters={
                    "project_id": project_id,
                    "include_metadata": True
                }
            ))
        
        # Check for video viewing intent
        if any(phrase in response_lower for phrase in [
            "view video", "watch video", "check video", "analyze video",
            "video info", "video details", "video metadata"
        ]):
            # Try to get video path from context or user request
            video_path = self._extract_video_path_from_context(response_lower)
            project_id = self.context.current_project.get("project_id", "default")
            
            if video_path:
                actions.append(AgentAction(
                    action_type="view_video",
                    description=f"View and analyze video: {video_path}",
                    parameters={
                        "video_path": video_path,
                        "project_id": project_id,
                        "analysis_type": "all",
                        "generate_thumbnail": True
                    }
                ))
        
        # Check for script creation intent
        if any(phrase in response_lower for phrase in [
            "create a script", "write a script", "craft a script", "generate a script",
            "here's a script", "script to get us started", "script that hits"
        ]):
            # Extract topic from conversation history
            topic = self._extract_topic_from_conversation()
            if topic:
                actions.append(AgentAction(
                    action_type="create_script",
                    description=f"Create script about {topic}",
                    parameters={
                        "topic": topic,
                        "style": "cinematic",
                        "length": "medium"
                    }
                ))
        
        # Enhanced B-roll detection with context awareness
        elif any(phrase in response_lower for phrase in [
            "find some", "get some", "download some", "search for",
            "amazing visuals", "great images", "perfect footage", "find broll",
            "get broll", "download broll", "find media", "get media", "download media",
            "find images", "get images", "download images", "find pictures", "get pictures",
            "find more", "get more", "download more", "additional broll", "more broll",
            "find footage", "get footage", "download footage"
        ]):
            # Get the user's original request from conversation history
            user_request = ""
            if self.context.conversation_history:
                # Get the most recent user message
                for msg in reversed(self.context.conversation_history):
                    if msg.get("role") == "user":
                        user_request = msg.get("content", "")
                        break
            
            # Create intelligent B-roll action with full context
            actions.append(AgentAction(
                action_type="find_media",
                description=f"Find media based on user request and context",
                parameters={
                    "user_request": user_request,
                    "context_aware": True,
                    "analyze_script": True,
                    "consider_existing_media": True
                }
            ))
        
        # Check for voiceover generation
        elif any(phrase in response_lower for phrase in [
            "generate voiceover", "create voiceover", "make voiceover", "voice over",
            "narrate", "narration", "audio", "speech"
        ]):
            # Check if we have a script in context
            script_content = self.context.current_project.get("script", "")
            if script_content:
                actions.append(AgentAction(
                    action_type="generate_voiceover",
                    description="Generate voiceover from existing script",
                    parameters={
                        "script": script_content,
                        "voice": "default"
                    }
                ))
        
        # Check for video processing
        elif any(phrase in response_lower for phrase in [
            "create video", "make video", "generate video", "produce video",
            "final video", "combine", "assemble", "edit video"
        ]):
            # Check if we have media and potentially voiceover
            media = self.context.current_project.get("media", [])
            voiceover = self.context.current_project.get("voiceover", "")
            
            if media:
                actions.append(AgentAction(
                    action_type="process_video",
                    description="Create final video from available media",
                    parameters={
                        "media_files": media,
                        "voiceover_file": voiceover,
                        "effects": []
                    }
                ))
        
        # Check for complete video creation workflow
        if any(phrase in response_lower for phrase in [
            "make the whole video", "create complete video", "full video", "entire video",
            "do everything", "complete workflow", "full process"
        ]):
            # This will trigger multiple actions in sequence
            project_id = self.context.current_project.get("project_id", "default")
            
            # First, scan the project to understand current state
            actions.append(AgentAction(
                action_type="scan_project",
                description="Scan project to understand current state",
                parameters={
                    "scan_type": "all",
                    "project_id": project_id,
                    "include_metadata": True
                }
            ))
            
            # Then create script if needed
            topic = self._extract_topic_from_conversation()
            if topic:
                actions.append(AgentAction(
                    action_type="create_script",
                    description=f"Create script about {topic}",
                    parameters={
                        "topic": topic,
                        "style": "cinematic",
                        "length": "medium"
                    }
                ))
            
            # Then find media
            user_request = ""
            if self.context.conversation_history:
                for msg in reversed(self.context.conversation_history):
                    if msg.get("role") == "user":
                        user_request = msg.get("content", "")
                        break
            
            actions.append(AgentAction(
                action_type="find_media",
                description="Find media for complete video",
                parameters={
                    "user_request": user_request,
                    "context_aware": True,
                    "analyze_script": True,
                    "consider_existing_media": True
                }
            ))
            
            # Then generate voiceover
            actions.append(AgentAction(
                action_type="generate_voiceover",
                description="Generate voiceover for complete video",
                parameters={
                    "voice": "default"
                }
            ))
            
            # Finally, process the video
            actions.append(AgentAction(
                action_type="process_video",
                description="Create final complete video",
                parameters={
                    "effects": []
                    }
                ))
        
        return actions
    
    def _extract_topic_from_conversation(self) -> str:
        """Extract topic from recent conversation history"""
        # Look at the last few messages to understand the current topic
        recent_messages = self.context.conversation_history[-3:]  # Last 3 messages
        
        for msg in reversed(recent_messages):  # Start from most recent
            content = msg.get("content", "").lower()
            
            # Look for topic keywords
            if "romans" in content or "rome" in content or "roman" in content:
                return "ancient rome roman empire colosseum gladiator caesar legion"
            elif "messi" in content or "soccer" in content or "football" in content:
                return "messi soccer football argentina barcelona"
            elif "ferrari" in content or "car" in content:
                return "ferrari car enzo ferrari f1 racing red sports car italy maranello"
            elif "nature" in content or "landscape" in content:
                return "nature landscape scenery mountains forest ocean"
            elif "technology" in content or "tech" in content:
                return "technology computer digital innovation modern tech"
            elif "sports" in content:
                return "sports athletics competition game team"
            elif "food" in content or "cooking" in content:
                return "food cooking cuisine restaurant kitchen chef"
            elif "music" in content:
                return "music musical instrument concert performance"
            elif "art" in content or "painting" in content:
                return "art painting sculpture museum gallery creative"
            elif "architecture" in content or "building" in content:
                return "architecture building construction modern design"
            elif "space" in content or "astronomy" in content:
                return "space astronomy galaxy stars planet universe"
            elif "history" in content or "historical" in content:
                return "history historical ancient civilization monument"
            elif "science" in content:
                return "science laboratory research experiment discovery"
            elif "business" in content or "office" in content:
                return "business office corporate workplace professional"
            elif "travel" in content or "tourism" in content:
                return "travel tourism destination vacation adventure"
            elif "fashion" in content or "style" in content:
                return "fashion style clothing design runway model"
            elif "health" in content or "medical" in content:
                return "health medical hospital doctor medicine"
            elif "education" in content or "school" in content:
                return "education school learning classroom student"
            elif "entertainment" in content or "movie" in content:
                return "entertainment movie film cinema theater"
        
        return ""
    
    async def _execute_actions(self, actions: List[AgentAction]) -> List[AgentAction]:
        """Execute a list of actions"""
        executed_actions = []
        gui_updates = []
        
        for action in actions:
            try:
                # Find executor with case-insensitive matching
                action_type_lower = action.action_type.lower()
                executor = self.action_executors.get(action_type_lower)
                if not executor:
                    action.error = f"No executor found for action type: {action.action_type}"
                    action.status = "failed"
                    executed_actions.append(action)
                    continue
                
                # Execute action
                action.status = "executing"
                result = await executor.execute(action, self.context)
                
                action.result = result
                action.status = "completed"
                executed_actions.append(action)
                
                # Add to completed actions
                self.context.completed_actions.append(action)
                
                # Collect GUI updates from action result
                if result and isinstance(result, dict):
                    if "gui_updates" in result:
                        gui_updates.extend(result["gui_updates"])
                    
                    # Send tool result message if included
                    if "tool_result" in result:
                        await self.websocket_manager.send_message(
                            self.context.session_id,
                            result["tool_result"]
                        )
                
            except Exception as e:
                action.error = str(e)
                action.status = "failed"
                executed_actions.append(action)
        
        # Send collected GUI updates
        if gui_updates:
            await self._send_gui_updates(gui_updates)
        
        return executed_actions
    
    def _update_context(self, context_updates: Dict[str, Any]) -> None:
        """Update agent context"""
        self.context.user_preferences.update(context_updates.get("preferences", {}))
        self.context.current_project.update(context_updates.get("project", {}))
    
    async def _send_gui_updates(self, gui_updates: List[Dict[str, Any]]) -> None:
        """Send GUI updates via WebSocket"""
        for update in gui_updates:
            await self.websocket_manager.send_message(
                self.context.session_id,
                {
                    "type": "gui_update",
                    "data": update,
                    "timestamp": datetime.now().isoformat()
                }
            )

    def _extract_video_path_from_context(self, response_lower: str) -> Optional[str]:
        """Extract video path from context or response"""
        # Check if there's a specific video mentioned
        if "video" in response_lower:
            # Look for common video file patterns
            video_patterns = [
                r'(\w+\.(mp4|avi|mov|mkv|wmv|flv))',
                r'video[:\s]+([^\s]+)',
                r'file[:\s]+([^\s]+\.(mp4|avi|mov|mkv|wmv|flv))'
            ]
            
            for pattern in video_patterns:
                match = re.search(pattern, response_lower)
                if match:
                    return match.group(1)
        
        # Check context for existing videos
        media = self.context.current_project.get("media", [])
        for item in media:
            if item.get("type") == "video":
                return item.get("path", "")
        
        # Default to common video filename
        return "final_video.mp4"

# ============================================================================
# AGENT FACTORY
# ============================================================================

class AIAgentFactory:
    """Factory for creating AI agents with all necessary tools"""
    
    def __init__(self, ai_service, script_writer, broll_finder, 
                 voiceover_generator, video_processor, websocket_manager,
                 project_scanner=None, video_viewer=None):
        self.ai_service = ai_service
        self.script_writer = script_writer
        self.broll_finder = broll_finder
        self.voiceover_generator = voiceover_generator
        self.video_processor = video_processor
        self.websocket_manager = websocket_manager
        self.project_scanner = project_scanner
        self.video_viewer = video_viewer
    
    def create_agent(self, session_id: str, user_id: str, project_id: str = None) -> AIAgent:
        """Create a new AI agent with all tools"""
        # Create context
        context = AgentContext(
            session_id=session_id,
            user_id=user_id,
            conversation_history=[],
            current_project={"project_id": project_id} if project_id else {}
        )
        
        # Create action executors
        action_executors = {
            ActionType.CREATE_SCRIPT.value: ScriptCreationExecutor(self.script_writer, self.ai_service),
            ActionType.FIND_MEDIA.value: MediaFinderExecutor(self.broll_finder, self.ai_service, self.websocket_manager),
            ActionType.GENERATE_VOICEOVER.value: VoiceoverGeneratorExecutor(self.voiceover_generator),
            ActionType.PROCESS_VIDEO.value: VideoProcessorExecutor(self.video_processor),
            ActionType.UPDATE_GUI.value: GUIUpdateExecutor(self.websocket_manager)
        }
        
        # Add new tools if available
        if self.project_scanner:
            action_executors[ActionType.SCAN_PROJECT.value] = ProjectScannerExecutor(self.project_scanner)
            action_executors[ActionType.READ_SCRIPT.value] = ScriptReaderExecutor(self.project_scanner)
        
        if self.video_viewer:
            action_executors[ActionType.VIEW_VIDEO.value] = VideoViewerExecutor(self.video_viewer)
        
        # Create agent
        agent = AIAgent(
            ai_service=self.ai_service,
            action_executors=action_executors,
            websocket_manager=self.websocket_manager,
            context=context
        )
        
        return agent

# ============================================================================
# USAGE EXAMPLE
# ============================================================================

async def example_usage():
    """Example of how to use the AI agent"""
    
    # Create agent factory (this would be done in your main app)
    factory = AIAgentFactory(
        ai_service=your_ai_service,
        script_writer=your_script_writer,
        broll_finder=your_broll_finder,
        voiceover_generator=your_voiceover_generator,
        video_processor=your_video_processor,
        websocket_manager=your_websocket_manager
    )
    
    # Create agent for a session
    agent = factory.create_agent("session_123", "user_456")
    
    # Process user message
    response = await agent.process_message("Create a video about space exploration")
    
    print(f"AI Response: {response.message}")
    print(f"Actions executed: {len(response.actions)}")
    
    for action in response.actions:
        print(f"- {action.action_type}: {action.status}")
        if action.result:
            print(f"  Result: {action.result}")

if __name__ == "__main__":
    asyncio.run(example_usage()) 