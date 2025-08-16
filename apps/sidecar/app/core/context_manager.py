"""
Context Manager for Sclip
Manages comprehensive context synchronization between frontend and AI brain
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from ..utils.logger import get_logger

logger = get_logger(__name__)

class ContextManager:
    """Manages comprehensive context for AI brain with full GUI state awareness"""
    
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.frontend_states: Dict[str, Dict[str, Any]] = {}
        self.ai_contexts: Dict[str, Dict[str, Any]] = {}
    
    def update_session_context(self, session_id: str, context_data: Dict[str, Any]) -> None:
        """Update session context with new data"""
        if session_id not in self.sessions:
            self.sessions[session_id] = {}
        
        self.sessions[session_id].update(context_data)
        self.sessions[session_id]["last_updated"] = datetime.now().isoformat()
        
        logger.info(f"Updated session context for {session_id}")
    
    def update_frontend_state(self, session_id: str, frontend_data: Dict[str, Any]) -> None:
        """Update frontend state for a session"""
        if session_id not in self.frontend_states:
            self.frontend_states[session_id] = {}
        
        self.frontend_states[session_id].update(frontend_data)
        self.frontend_states[session_id]["last_updated"] = datetime.now().isoformat()
        
        logger.info(f"Updated frontend state for {session_id}")
    
    def update_ai_context(self, session_id: str, ai_data: Dict[str, Any]) -> None:
        """Update AI context for a session"""
        if session_id not in self.ai_contexts:
            self.ai_contexts[session_id] = {}
        
        self.ai_contexts[session_id].update(ai_data)
        self.ai_contexts[session_id]["last_updated"] = datetime.now().isoformat()
        
        logger.info(f"Updated AI context for {session_id}")
    
    def update_conversation_history(self, session_id: str, role: str, content: str) -> None:
        """Update conversation history for a session"""
        if session_id not in self.sessions:
            self.sessions[session_id] = {}
        
        session = self.sessions[session_id]
        
        # Initialize conversation history if it doesn't exist
        if "conversation_history" not in session:
            session["conversation_history"] = []
        
        # Add new message to conversation history
        session["conversation_history"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 50 messages to prevent memory issues
        if len(session["conversation_history"]) > 50:
            session["conversation_history"] = session["conversation_history"][-50:]
        
        logger.info(f"Updated conversation history for session {session_id}")
    
    def update_workflow_results(self, session_id: str, workflow_id: str, results: Dict[str, Any]) -> None:
        """Update session with workflow results"""
        if session_id not in self.sessions:
            self.sessions[session_id] = {}
        
        session = self.sessions[session_id]
        
        # Store workflow results
        if "workflow_results" not in session:
            session["workflow_results"] = {}
        
        session["workflow_results"][workflow_id] = {
            "results": results,
            "timestamp": asyncio.get_event_loop().time(),
            "execution_time": results.get("execution_time", 0),
            "steps_completed": results.get("steps_completed", 0),
            "total_steps": results.get("total_steps", 0)
        }
        
        # Update project assets based on results
        if "results" in results:
            for step_id, step_result in results["results"].items():
                if step_result.get("success", False):
                    self._update_assets_from_result(session_id, step_result)
        
        logger.info(f"Updated workflow results for session {session_id}, workflow {workflow_id}")
    
    def _update_assets_from_result(self, session_id: str, result: Dict[str, Any]) -> None:
        """Update session assets based on tool result"""
        session = self.sessions.get(session_id, {})
        
        tool_name = result.get("tool", "")
        
        if tool_name == "script_writer":
            # Update scripts
            if "scripts" not in session:
                session["scripts"] = []
            
            script_content = result.get("result", "")
            if script_content:
                session["scripts"].append({
                    "id": f"script_{len(session['scripts'])}",
                    "content": script_content,
                    "timestamp": asyncio.get_event_loop().time(),
                    "tool": tool_name
                })
        
        elif tool_name == "broll_finder":
            # Update media files
            if "media_files" not in session:
                session["media_files"] = []
            
            downloaded_files = result.get("result", {}).get("downloaded_files", [])
            for file_path in downloaded_files:
                session["media_files"].append({
                    "id": f"media_{len(session['media_files'])}",
                    "path": file_path,
                    "type": "image" if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')) else "video",
                    "timestamp": asyncio.get_event_loop().time(),
                    "tool": tool_name
                })
        
        elif tool_name == "voiceover_generator":
            # Update voiceovers
            if "voiceovers" not in session:
                session["voiceovers"] = []
            
            voiceover_path = result.get("result", {}).get("voiceover_path", "")
            if voiceover_path:
                session["voiceovers"].append({
                    "id": f"voiceover_{len(session['voiceovers'])}",
                    "path": voiceover_path,
                    "timestamp": asyncio.get_event_loop().time(),
                    "tool": tool_name
                })
        
        elif tool_name == "video_processor":
            # Update videos
            if "videos" not in session:
                session["videos"] = []
            
            video_path = result.get("result", {}).get("final_video", "")
            if video_path:
                session["videos"].append({
                    "id": f"video_{len(session['videos'])}",
                    "path": video_path,
                    "timestamp": asyncio.get_event_loop().time(),
                    "tool": tool_name
                })
    
    def get_comprehensive_context(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive context combining all sources"""
        context = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "session_data": self.sessions.get(session_id, {}),
            "frontend_state": self.frontend_states.get(session_id, {}),
            "ai_context": self.ai_contexts.get(session_id, {}),
            "project_state": self._build_project_state(session_id),
            "conversation_history": self._get_conversation_history(session_id),
            "media_inventory": self._get_media_inventory(session_id),
            "script_content": self._get_script_content(session_id),
            "voiceover_info": self._get_voiceover_info(session_id),
            "video_info": self._get_video_info(session_id)
        }
        
        return context
    
    def _build_project_state(self, session_id: str) -> Dict[str, Any]:
        """Build comprehensive project state"""
        session_data = self.sessions.get(session_id, {})
        frontend_state = self.frontend_states.get(session_id, {})
        ai_context = self.ai_contexts.get(session_id, {})
        
        project_state = {
            "project_id": session_data.get("project_id") or frontend_state.get("project_id"),
            "script": self._get_script_content(session_id),
            "media": self._get_media_inventory(session_id),
            "voiceover": self._get_voiceover_info(session_id),
            "final_video": self._get_video_info(session_id),
            "user_preferences": session_data.get("user_preferences", {}),
            "conversation_history": self._get_conversation_history(session_id),
            "completed_actions": session_data.get("completed_actions", []),
            "current_step": session_data.get("current_step", "idle"),
            "status": session_data.get("status", "active")
        }
        
        return project_state
    
    def _get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history from all sources"""
        session_data = self.sessions.get(session_id, {})
        ai_context = self.ai_contexts.get(session_id, {})
        
        # Combine conversation history from different sources
        history = []
        
        # From session data
        if "conversation_history" in session_data:
            history.extend(session_data["conversation_history"])
        
        # From AI context
        if "conversation_history" in ai_context:
            history.extend(ai_context["conversation_history"])
        
        # Remove duplicates and sort by timestamp
        unique_history = []
        seen_messages = set()
        
        for msg in history:
            msg_key = f"{msg.get('role', '')}:{msg.get('content', '')[:50]}"
            if msg_key not in seen_messages:
                seen_messages.add(msg_key)
                unique_history.append(msg)
        
        return unique_history[-20:]  # Last 20 messages
    
    def _get_media_inventory(self, session_id: str) -> List[Dict[str, Any]]:
        """Get comprehensive media inventory"""
        session_data = self.sessions.get(session_id, {})
        frontend_state = self.frontend_states.get(session_id, {})
        ai_context = self.ai_contexts.get(session_id, {})
        
        media = []
        
        # From session data
        if "media" in session_data:
            media.extend(session_data["media"])
        
        # From frontend state
        if "projectFiles" in frontend_state:
            for file in frontend_state["projectFiles"]:
                if file.get("type") in ["image", "video", "audio"]:
                    media.append({
                        "name": file.get("name", ""),
                        "type": file.get("type", ""),
                        "path": file.get("path", ""),
                        "url": file.get("url", ""),
                        "size": file.get("size", 0),
                        "source": "frontend"
                    })
        
        # From AI context
        if "media" in ai_context:
            media.extend(ai_context["media"])
        
        return media
    
    def _get_script_content(self, session_id: str) -> str:
        """Get script content from all sources"""
        session_data = self.sessions.get(session_id, {})
        frontend_state = self.frontend_states.get(session_id, {})
        ai_context = self.ai_contexts.get(session_id, {})
        
        # Try different sources in order of priority
        script = ""
        
        # 1. Check session data first (most recent)
        if session_data.get("script"):
            script = session_data["script"]
        
        # 2. Check frontend scripts array (what's actually in the GUI)
        elif frontend_state.get("scripts"):
            scripts_array = frontend_state["scripts"]
            if scripts_array and len(scripts_array) > 0:
                # Get the latest script
                latest_script = scripts_array[-1]
                script = latest_script.get("content", "")
        
        # 3. Check AI context
        elif ai_context.get("script"):
            script = ai_context["script"]
        
        # 4. Check frontend state for direct script field
        elif frontend_state.get("script"):
            script = frontend_state["script"]
        
        logger.info(f"Retrieved script content for session {session_id}: {len(script)} characters")
        if script:
            logger.info(f"Script preview: {script[:100]}...")
        
        return script
    
    def _get_voiceover_info(self, session_id: str) -> Dict[str, Any]:
        """Get voiceover information"""
        session_data = self.sessions.get(session_id, {})
        frontend_state = self.frontend_states.get(session_id, {})
        ai_context = self.ai_contexts.get(session_id, {})
        
        voiceover = (
            session_data.get("voiceover") or
            frontend_state.get("voiceover") or
            ai_context.get("voiceover") or
            {}
        )
        
        return voiceover if isinstance(voiceover, dict) else {"file": voiceover}
    
    def _get_video_info(self, session_id: str) -> Dict[str, Any]:
        """Get video information"""
        session_data = self.sessions.get(session_id, {})
        frontend_state = self.frontend_states.get(session_id, {})
        ai_context = self.ai_contexts.get(session_id, {})
        
        video = (
            session_data.get("final_video") or
            frontend_state.get("final_video") or
            ai_context.get("final_video") or
            {}
        )
        
        return video if isinstance(video, dict) else {"file": video}
    
    def sync_with_frontend_store(self, session_id: str, frontend_store_data: Dict[str, Any]) -> None:
        """Sync with frontend Zustand store data"""
        try:
            # Extract relevant data from frontend store
            frontend_state = {
                "projectFiles": frontend_store_data.get("projectFiles", []),
                "scripts": frontend_store_data.get("scripts", []),
                "videoPreviews": frontend_store_data.get("videoPreviews", []),
                "userContext": frontend_store_data.get("userContext", {}),
                "messages": frontend_store_data.get("messages", [])
            }
            
            # Update frontend state
            self.update_frontend_state(session_id, frontend_state)
            
            # Extract script content from scripts array and make it available to AI
            if frontend_store_data.get("scripts"):
                scripts_array = frontend_store_data["scripts"]
                if scripts_array and len(scripts_array) > 0:
                    # Get the latest script
                    latest_script = scripts_array[-1]
                    script_content = latest_script.get("content", "")
                    if script_content:
                        # Update both session context and AI context with script
                        self.update_session_context(session_id, {"script": script_content})
                        self.update_ai_context(session_id, {"script": script_content})
                        logger.info(f"Extracted script content from frontend store: {len(script_content)} characters")
                        logger.info(f"Script preview: {script_content[:100]}...")
            
            logger.info(f"Synced frontend store data for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error syncing with frontend store: {e}")
    
    def get_ai_context_prompt(self, session_id: str, user_message: str) -> str:
        """Generate comprehensive AI context prompt"""
        context = self.get_comprehensive_context(session_id)
        
        # Build conversation history
        conversation_text = ""
        for msg in context["conversation_history"][-10:]:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            conversation_text += f"{role}: {content}\n"
        
        # Build project state with prominent script section
        project_state = ""
        
        # Make script content very prominent
        if context["script_content"]:
            script_content = context["script_content"]
            project_state += f"""🎬 **CURRENT SCRIPT CONTENT** (Available for B-roll search and video creation):
{script_content}

"""
        else:
            project_state += "⚠️ **NO SCRIPT AVAILABLE** - User needs to create a script first.\n\n"
        
        if context["media_inventory"]:
            media_list = []
            for media in context["media_inventory"][-10:]:
                media_info = f"- {media.get('name', 'Unknown')} ({media.get('type', 'unknown')})"
                if media.get('source'):
                    media_info += f" [Source: {media.get('source')}]"
                media_list.append(media_info)
            project_state += f"📁 **EXISTING MEDIA** ({len(context['media_inventory'])} items):\n" + "\n".join(media_list) + "\n\n"
        
        if context["voiceover_info"]:
            project_state += f"🎤 **VOICEOVER**: {json.dumps(context['voiceover_info'], indent=2)}\n\n"
        
        if context["video_info"]:
            project_state += f"🎥 **FINAL VIDEO**: {json.dumps(context['video_info'], indent=2)}\n\n"
        
        # Build user preferences
        preferences = ""
        if context["project_state"]["user_preferences"]:
            preferences = f"User preferences: {json.dumps(context['project_state']['user_preferences'], indent=2)}\n"
        
        return f"""
You are Sclip, an AI video creation assistant with full context awareness.

**🎯 CONTEXT AWARENESS:**
You have complete visibility into the current project state. When users ask for B-roll or media, ALWAYS check the current script content first and use it to find relevant media.

**📋 CURRENT PROJECT STATE:**
{project_state}

**💬 CONVERSATION HISTORY:**
{conversation_text}

**⚙️ USER PREFERENCES:**
{preferences}

**📝 USER MESSAGE:** {user_message}

**🔍 IMPORTANT CONTEXT RULES:**
1. If a script exists, use its content to find relevant B-roll media
2. If no script exists, ask the user to create one first
3. Always reference the current script when suggesting media
4. The script content above is what's currently loaded in the GUI
5. Use script keywords and themes to find matching media

You have complete visibility into the current project state, including:
- ✅ Script content and any edits (see above)
- ✅ All downloaded media and their sources
- ✅ Voiceover files if generated
- ✅ Final video if created
- ✅ Complete conversation history
- ✅ User preferences and style choices

Use this comprehensive context to provide intelligent, context-aware responses and actions.
"""

    def get_enhanced_context_for_ai(self, session_id: str, user_message: str) -> str:
        """Get enhanced context for AI with better structure and memory"""
        
        # Get basic context
        basic_context = self.get_ai_context_prompt(session_id, user_message)
        
        # Add enhanced context components
        enhanced_context = f"""
**ENHANCED CONTEXT FOR AGENTIC WORKFLOW**

**CURRENT SESSION STATE:**
- Session ID: {session_id}
- User Message: {user_message}
- Project ID: {self.sessions.get(session_id, {}).get('project_id', 'None')}

**CONVERSATION HISTORY (Last 5 messages):**
{self._format_conversation_history(session_id)}

**PROJECT ASSETS:**
{self._format_project_assets(session_id)}

**USER PREFERENCES:**
{self._format_user_preferences(session_id)}

**RECENT TOOL EXECUTIONS:**
{self._format_tool_executions(session_id)}

**WORKFLOW STATE:**
{self._format_workflow_state(session_id)}

**CONTEXT SUMMARY:**
{basic_context}
"""
        
        return enhanced_context
    
    def _format_conversation_history(self, session_id: str) -> str:
        """Format conversation history for AI context"""
        session = self.sessions.get(session_id, {})
        history = session.get('conversation_history', [])
        
        if not history:
            return "No conversation history available."
        
        formatted_history = []
        for i, msg in enumerate(history[-5:]):  # Last 5 messages
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')[:200]  # Limit length
            formatted_history.append(f"{i+1}. {role.upper()}: {content}")
        
        return "\n".join(formatted_history)
    
    def _format_project_assets(self, session_id: str) -> str:
        """Format project assets for AI context"""
        session = self.sessions.get(session_id, {})
        project_id = session.get('project_id')
        
        if not project_id:
            return "No active project."
        
        assets = {
            'scripts': session.get('scripts', []),
            'media_files': session.get('media_files', []),
            'voiceovers': session.get('voiceovers', []),
            'videos': session.get('videos', [])
        }
        
        formatted_assets = []
        for asset_type, asset_list in assets.items():
            if asset_list:
                formatted_assets.append(f"- {asset_type.title()}: {len(asset_list)} items")
                for asset in asset_list[:3]:  # Show first 3 items
                    formatted_assets.append(f"  * {asset.get('name', 'Unknown')}")
        
        return "\n".join(formatted_assets) if formatted_assets else "No assets in current project."
    
    def _format_user_preferences(self, session_id: str) -> str:
        """Format user preferences for AI context"""
        session = self.sessions.get(session_id, {})
        preferences = session.get('user_preferences', {})
        
        if not preferences:
            return "No user preferences set."
        
        formatted_prefs = []
        for key, value in preferences.items():
            formatted_prefs.append(f"- {key}: {value}")
        
        return "\n".join(formatted_prefs)
    
    def _format_tool_executions(self, session_id: str) -> str:
        """Format recent tool executions for AI context"""
        session = self.sessions.get(session_id, {})
        executions = session.get('tool_executions', [])
        
        if not executions:
            return "No recent tool executions."
        
        formatted_executions = []
        for i, execution in enumerate(executions[-3:]):  # Last 3 executions
            tool_name = execution.get('tool', 'unknown')
            status = execution.get('status', 'unknown')
            timestamp = execution.get('timestamp', 'unknown')
            formatted_executions.append(f"{i+1}. {tool_name}: {status} ({timestamp})")
        
        return "\n".join(formatted_executions)
    
    def _format_workflow_state(self, session_id: str) -> str:
        """Format current workflow state for AI context"""
        session = self.sessions.get(session_id, {})
        workflow_state = session.get('workflow_state', {})
        
        if not workflow_state:
            return "No active workflow."
        
        current_step = workflow_state.get('current_step', 'None')
        total_steps = workflow_state.get('total_steps', 0)
        completed_steps = workflow_state.get('completed_steps', 0)
        status = workflow_state.get('status', 'unknown')
        
        return f"""
- Current Step: {current_step}
- Progress: {completed_steps}/{total_steps} steps completed
- Status: {status}
- Estimated Time Remaining: {workflow_state.get('estimated_time_remaining', 'Unknown')}
"""

# Global context manager instance
context_manager = ContextManager() 