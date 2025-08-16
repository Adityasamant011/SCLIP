"""
Sclip FastAPI Backend - Phase 3.1 Implementation
Main application entry point with all endpoints and WebSocket support
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid
from pathlib import Path
import os

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, UploadFile, File, Query, BackgroundTasks, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse, Response
from fastapi.requests import Request
from pydantic import BaseModel, ValidationError
import mimetypes

from app.tools.script_writer import ScriptWriterTool
from app.tools.broll_finder import BrollFinderTool
from app.tools.voiceover_generator import VoiceoverGeneratorTool
from app.tools.video_processor import VideoProcessorTool
from app.tools.project_scanner import ProjectScannerTool
from app.tools.video_viewer import VideoViewerTool
from app.services.google_search import google_search_service
from app.services.pexels_api import pexels_api_service
from app.services.media_downloader import media_downloader_service
from app.utils.logger import get_logger
from config import settings
from app.utils.input_validator import InputValidator
from app.orchestrator.sclip_brain import SclipBrain
from app.core.professional_handler import ProfessionalMessageHandler, setup_professional_system
from app.core.context_manager import context_manager
input_validator = InputValidator()

# --- 3.2: Real-Time Streaming Infrastructure Additions ---
import threading
import shutil

# Add message queue per session (last 100 messages)
MESSAGE_QUEUE_SIZE = 100
message_queues: Dict[str, List[Dict[str, Any]]] = {}
message_queues_lock = threading.Lock()

def add_message_to_queue(session_id: str, message: Dict[str, Any]):
    with message_queues_lock:
        if session_id not in message_queues:
            message_queues[session_id] = []
        message_queues[session_id].append(message)
        if len(message_queues[session_id]) > MESSAGE_QUEUE_SIZE:
            message_queues[session_id] = message_queues[session_id][-MESSAGE_QUEUE_SIZE:]

def get_messages_since(session_id: str, last_message_id: str = None):
    with message_queues_lock:
        queue = message_queues.get(session_id, [])
        if not last_message_id:
            return queue
        for idx, msg in enumerate(queue):
            if msg.get("message_id") == last_message_id:
                return queue[idx+1:]
        return queue  # If not found, return all

logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Sclip Backend",
    description="AI-powered video editing backend with agentic orchestration",
    version="1.0.0"
)

# Configure CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:5173", 
        "http://127.0.0.1:3000",
        "http://localhost:1420",
        "http://127.0.0.1:1420",
        "http://[::1]:1420",
        "tauri://localhost",
        "http://localhost:1421",
        "http://127.0.0.1:1421",
        "http://[::1]:1421"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import new AI agent and services
from app.core.true_ai_agent import TrueAIAgent
from app.services.rag_service import rag_service
from app.tools.enhanced_mcp import enhanced_mcp

# Initialize tools
script_writer_tool = ScriptWriterTool()
broll_finder_tool = BrollFinderTool()
voiceover_generator_tool = VoiceoverGeneratorTool()
video_processor_tool = VideoProcessorTool()
project_scanner_tool = ProjectScannerTool()
video_viewer_tool = VideoViewerTool()

# Initialize enhanced MCP and register tools
enhanced_mcp.register_tool(script_writer_tool)
enhanced_mcp.register_tool(broll_finder_tool)
enhanced_mcp.register_tool(voiceover_generator_tool)
enhanced_mcp.register_tool(video_processor_tool)
enhanced_mcp.register_tool(project_scanner_tool)
enhanced_mcp.register_tool(video_viewer_tool)

# Initialize True AI Agent
true_ai_agent = None  # Will be initialized in startup event

# Patch ConnectionManager to use message queue and support authentication
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_connections: Dict[str, List[str]] = {}
        self.connection_auth: Dict[str, str] = {}  # connection_id -> user_id or token
        self.session_processing: Dict[str, bool] = {}  # Track if session is processing
    
    async def connect(self, websocket: WebSocket, session_id: str, user_id: str = None, last_message_id: str = None):
        # Only accept and register, do not replay messages here
        # (Replay is now handled in websocket_endpoint after connection_established)
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        self.active_connections[connection_id] = websocket
        if session_id not in self.session_connections:
            self.session_connections[session_id] = []
        self.session_connections[session_id].append(connection_id)
        if user_id:
            self.connection_auth[connection_id] = user_id
        logger.info(f"WebSocket connected: {connection_id} for session: {session_id} user: {user_id}")
        return connection_id
    
    def disconnect(self, connection_id: str, session_id: str):
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if connection_id in self.connection_auth:
            del self.connection_auth[connection_id]
        if session_id in self.session_connections:
            if connection_id in self.session_connections[session_id]:
                self.session_connections[session_id].remove(connection_id)
            if not self.session_connections[session_id]:
                del self.session_connections[session_id]
        logger.info(f"WebSocket disconnected: {connection_id} from session: {session_id}")
    
    async def send_message(self, session_id: str, message: Dict[str, Any]):
        # Add message_id and timestamp
        message = dict(message)  # copy
        message["message_id"] = message.get("message_id") or str(uuid.uuid4())
        message["timestamp"] = message.get("timestamp") or datetime.now().isoformat()
        add_message_to_queue(session_id, message)
        if session_id in self.session_connections:
            for connection_id in self.session_connections[session_id]:
                if connection_id in self.active_connections:
                    try:
                        await self.active_connections[connection_id].send_text(json.dumps(message))
                    except Exception as e:
                        logger.error(f"Error sending message to {connection_id}: {e}")
                        self.disconnect(connection_id, session_id)
    
    async def broadcast_to_session(self, session_id: str, message: Dict[str, Any]):
        """Broadcast message to all connections in a session"""
        await self.send_message(session_id, message)

manager = ConnectionManager()

# Pydantic models for request/response validation
class PromptRequest(BaseModel):
    prompt: str
    style: str = "cinematic"
    length: str = "medium"
    tone: str = "professional"
    approval_mode: str = "auto_approve"
    quality_setting: str = "standard"

class ApprovalRequest(BaseModel):
    session_id: str
    step: str
    action: str  # "approve", "reject", "modify"
    modifications: Dict[str, Any] = {}

class SessionInfo(BaseModel):
    session_id: str
    status: str
    current_step: str
    progress: float
    created_at: datetime
    updated_at: datetime

# Session state management
sessions: Dict[str, Dict[str, Any]] = {}

def create_session_id() -> str:
    """Generate unique session ID"""
    return f"session_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"

def get_session(session_id: str) -> Dict[str, Any]:
    """Get session state"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return sessions[session_id]

def update_session(session_id: str, updates: Dict[str, Any]):
    """Update session state"""
    if session_id not in sessions:
        sessions[session_id] = {
            "session_id": session_id,
            "status": "created",
            "current_step": "initialized",
            "progress": 0.0,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "tool_outputs": {},
            "user_approvals": [],
            "errors": []
        }
    
    sessions[session_id].update(updates)
    sessions[session_id]["updated_at"] = datetime.now()

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "services": {
            "script_writer": "available",
            "broll_finder": "available", 
            "voiceover_generator": "available",
            "video_processor": "available",
            "google_search": "available",
            "pexels_api": "available",
            "media_downloader": "available"
        }
    }

# Main prompt endpoint
@app.post("/api/prompt")
async def submit_prompt(request: PromptRequest):
    """Submit user prompt and start orchestration"""
    try:
        session_id = create_session_id()
        
        # Initialize session
        update_session(session_id, {
            "prompt": request.prompt,
            "style": request.style,
            "length": request.length,
            "tone": request.tone,
            "approval_mode": request.approval_mode,
            "quality_setting": request.quality_setting,
            "status": "processing",
            "current_step": "planning"
        })
        
        # Send initial response - let AI determine if it's a video request or chat
        await manager.send_message(session_id, {
            "type": "ai_message",
            "content": "Processing your request...",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        })
        
        # Start async orchestration
        asyncio.create_task(run_orchestration(session_id, request))
        
        return {
            "session_id": session_id,
            "status": "started",
            "message": "Video creation process started"
        }
        
    except Exception as e:
        logger.error(f"Error submitting prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time updates
@app.websocket("/api/stream/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, user_id: str = Query(None), last_message_id: str = Query(None)):
    """WebSocket endpoint for real-time streaming (with replay/auth)
    Guarantees 'connection_established' is always the first message sent."""
    connection_id = None
    try:
        # Accept connection and register
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        manager.active_connections[connection_id] = websocket
        if session_id not in manager.session_connections:
            manager.session_connections[session_id] = []
        manager.session_connections[session_id].append(connection_id)
        if user_id:
            manager.connection_auth[connection_id] = user_id
        logger.info(f"WebSocket connected: {connection_id} for session: {session_id} user: {user_id}")
        # Guarantee: send connection_established synchronously before any orchestration or background task
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "message_id": str(uuid.uuid4())
        }))
        # Now replay missed messages (if any) after connection_established
        missed = get_messages_since(session_id, last_message_id)
        for msg in missed:
            try:
                await websocket.send_text(json.dumps(msg))
            except Exception as e:
                logger.error(f"Error sending replay message to {connection_id}: {e}")
        # Now enter receive loop
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                logger.info(f"Received WebSocket message: {message.get('type', 'unknown')}")
                
                # Handle different message types
                if message.get("type") == "user_message":
                    await handle_user_message(session_id, message)
                elif message.get("type") == "ping":
                    # Respond to ping with pong
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }))
                elif message.get("type") == "heartbeat":
                    # Respond to heartbeat
                    await websocket.send_text(json.dumps({
                        "type": "heartbeat_ack",
                        "timestamp": datetime.now().isoformat()
                    }))
                else:
                    logger.info(f"Unhandled message type: {message.get('type')}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in WebSocket message: {e}")
                # Send error response to client
                try:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format",
                        "timestamp": datetime.now().isoformat()
                    }))
                except:
                    break
                continue
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected normally: {connection_id}")
                break
            except Exception as e:
                logger.error(f"Error in WebSocket receive loop: {e}")
                # Send error response to client before breaking
                try:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Internal server error",
                        "timestamp": datetime.now().isoformat()
                    }))
                except:
                    pass
                break
    except WebSocketDisconnect:
        if connection_id:
            manager.disconnect(connection_id, session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if connection_id:
            manager.disconnect(connection_id, session_id)

# --- GLOBAL OPTIONS HANDLER FOR CORS ---
@app.options("/{rest_of_path:path}")
def options_handler(rest_of_path: str):
    return Response(status_code=204)

# User approval endpoint (robust input handling)
@app.post("/api/approve/{session_id}")
async def user_approval(session_id: str, request: dict = Body(...)):
    """Handle user approvals and modifications (robust)"""
    try:
        try:
            session = get_session(session_id)
        except KeyError:
            logger.error(f"Session not found: {session_id}")
            return JSONResponse(status_code=404, content={"detail": "Session not found"})
        except Exception as e:
            logger.error(f"Unexpected error in get_session: {e}")
            return JSONResponse(status_code=404, content={"detail": "Session not found"})
        # Validate input
        step = request.get("step")
        action = request.get("action")
        modifications = request.get("modifications", {})
        if not step or not action:
            return JSONResponse(status_code=422, content={"detail": "Missing required fields: step, action"})
        # Update session with user decision
        session["user_approvals"].append({
            "step": step,
            "action": action,
            "modifications": modifications,
            "timestamp": datetime.now().isoformat()
        })
        # Send approval confirmation
        await manager.send_message(session_id, {
            "type": "approval_received",
            "step": step,
            "action": action,
            "timestamp": datetime.now().isoformat()
        })
        # Continue orchestration if needed
        if action == "approve":
            asyncio.create_task(continue_orchestration(session_id))
        return {"status": "approved", "message": f"Step {step} approved"}
    except Exception as e:
        logger.error(f"Error handling approval: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})

# Session management endpoints
@app.get("/api/sessions")
async def list_sessions():
    """List all user sessions"""
    try:
        session_list = []
        for session_id, session_data in sessions.items():
            session_list.append(SessionInfo(
                session_id=session_id,
                status=session_data.get("status", "unknown"),
                current_step=session_data.get("current_step", "unknown"),
                progress=session_data.get("progress", 0.0),
                created_at=session_data.get("created_at", datetime.now()),
                updated_at=session_data.get("updated_at", datetime.now())
            ))
        
        return {"sessions": session_list}
        
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}")
async def get_session_info(session_id: str):
    """Get detailed session information"""
    try:
        session = get_session(session_id)
        return SessionInfo(
            session_id=session_id,
            status=session.get("status", "unknown"),
            current_step=session.get("current_step", "unknown"),
            progress=session.get("progress", 0.0),
            created_at=session.get("created_at", datetime.now()),
            updated_at=session.get("updated_at", datetime.now())
        )
        
    except Exception as e:
        logger.error(f"Error getting session info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# File management endpoints
@app.get("/api/files/list/{session_id}")
async def list_session_files(session_id: str, limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0), type: str = Query(None), name: str = Query(None)):
    """List files for a session with pagination and filtering"""
    try:
        if session_id not in sessions:
            return {
                "session_id": session_id,
                "files": [],
                "message": "Session not found or no files available"
            }
        files = sessions[session_id].get("files", [])
        # Filtering
        if type:
            files = [f for f in files if f.get("type") == type]
        if name:
            files = [f for f in files if name.lower() in f["filename"].lower()]
        # Pagination
        files = files[offset:offset+limit]
        return {
            "session_id": session_id,
            "files": files
        }
    except Exception as e:
        logger.error(f"Error listing session files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def compress_and_optimize_file(file_path: Path, file_type: str) -> Path:
    """Stub for file compression/optimization. For now, just return original file. Extend in future."""
    logger.info(f"Compress/optimize called for {file_path} type {file_type}")
    # TODO: Implement real compression/optimization
    return file_path

@app.post("/api/files/upload")
async def upload_file(session_id: str, file: UploadFile = File(...)):
    """Upload file for a session with strong validation and sanitization (robust)"""
    try:
        # Validate session exists
        if session_id not in sessions:
            return JSONResponse(status_code=404, content={"detail": "Session not found"})
        # Validate file type by extension
        file_ext = Path(file.filename).suffix.lower()
        allowed_types = input_validator.allowed_file_types
        detected_type = None
        for t, exts in allowed_types.items():
            if file_ext in exts:
                detected_type = t
                break
        if not detected_type:
            return JSONResponse(status_code=400, content={"detail": f"File type {file_ext} not allowed"})
        # Validate file size
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        if file_size > input_validator.file_size_limits[detected_type]:
            return JSONResponse(status_code=413, content={"detail": "File too large"})
        # Save file to session directory with sanitized filename
        session_dir = Path(settings.sessions_dir) / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        safe_filename = input_validator._sanitize_filename(file.filename)
        file_path = session_dir / safe_filename
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        # Validate file content
        try:
            input_validator.validate_file_upload(str(file_path), detected_type)
        except Exception as e:
            file_path.unlink(missing_ok=True)
            return JSONResponse(status_code=400, content={"detail": f"File content validation failed: {e}"})
        # Compress/optimize file (stub)
        file_path = compress_and_optimize_file(file_path, detected_type)
        # Add file to session
        if "files" not in sessions[session_id]:
            sessions[session_id]["files"] = []
        # Add file info
        sessions[session_id]["files"].append({
            "filename": safe_filename,
            "path": str(file_path),
            "type": detected_type,
            "size": file_size
        })
        return {"status": "uploaded", "filename": safe_filename}
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.get("/api/files/download/{session_id}/{filename}")
async def download_file(session_id: str, filename: str):
    """Download file from a session"""
    try:
        # Validate session exists
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Check if file exists in session
        session_files = sessions[session_id].get("files", [])
        file_info = None
        for f in session_files:
            if f["filename"] == filename:
                file_info = f
                break
        
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_path = Path(file_info["path"])
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/octet-stream"
        )
        
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files/preview/{session_id}/{filename}")
async def preview_file(session_id: str, filename: str):
    """Preview a file (image/video/audio) from a session with correct content-type (robust)"""
    try:
        if session_id not in sessions:
            return JSONResponse(status_code=404, content={"detail": "Session not found"})
        session_files = sessions[session_id].get("files", [])
        file_info = next((f for f in session_files if f["filename"] == filename), None)
        if not file_info:
            return JSONResponse(status_code=404, content={"detail": "File not found"})
        file_path = Path(file_info["path"])
        if not file_path.exists():
            return JSONResponse(status_code=404, content={"detail": "File not found on disk"})
        mime, _ = mimetypes.guess_type(str(file_path))
        if not mime:
            mime = "application/octet-stream"
        # Only allow preview for images, audio, video
        if not (mime.startswith("image/") or mime.startswith("video/") or mime.startswith("audio/")):
            return JSONResponse(status_code=415, content={"detail": "Preview not supported for this file type"})
        return FileResponse(file_path, media_type=mime, filename=filename)
    except Exception as e:
        logger.error(f"Error previewing file: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.delete("/api/files/delete/{session_id}/{filename}")
async def delete_file(session_id: str, filename: str):
    """Delete a file from a session (disk and session record)"""
    try:
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        session_files = sessions[session_id].get("files", [])
        file_info = next((f for f in session_files if f["filename"] == filename), None)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        file_path = Path(file_info["path"])
        if file_path.exists():
            file_path.unlink()
        # Remove from session record
        sessions[session_id]["files"] = [f for f in session_files if f["filename"] != filename]
        return {"message": "File deleted", "filename": filename, "session_id": session_id}
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Asset endpoints for desktop app
@app.get("/assets/effects")
async def get_effects():
    """Get available effects"""
    try:
        effects = video_processor_tool.get_available_effects()
        return {"effects": effects}
    except Exception as e:
        logger.error(f"Error getting effects: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/assets/filters")
async def get_filters():
    """Get available filters"""
    try:
        filters = video_processor_tool.get_available_filters()
        return {"filters": filters}
    except Exception as e:
        logger.error(f"Error getting filters: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/assets/transitions")
async def get_transitions():
    """Get available transitions"""
    try:
        transitions = video_processor_tool.get_available_transitions()
        return {"transitions": transitions}
    except Exception as e:
        logger.error(f"Error getting transitions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Preview endpoints for desktop app
# Helper to get absolute preview path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
PREVIEW_CACHE = PROJECT_ROOT / "resources" / "preview_cache"
SIDECAR_PREVIEW_CACHE = Path(__file__).parent.parent.parent / "resources" / "preview_cache"

@app.get("/preview/effect/{effect_id}")
async def get_effect_preview(effect_id: str):
    """Get effect preview"""
    try:
        # Try main resources first, then sidecar resources
        preview_path = PREVIEW_CACHE / f"effect_{effect_id}.gif"
        if not preview_path.exists():
            preview_path = SIDECAR_PREVIEW_CACHE / f"effect_{effect_id}.gif"
        
        logger.info(f"Looking for effect preview: {preview_path}")
        logger.info(f"Path exists: {preview_path.exists()}")
        if preview_path.exists():
            from fastapi.responses import FileResponse
            return FileResponse(preview_path)
        raise HTTPException(status_code=404, detail=f"Effect preview not found: {effect_id}")
    except Exception as e:
        logger.error(f"Error getting effect preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/preview/filter/{filter_id}")
async def get_filter_preview(filter_id: str):
    """Get filter preview"""
    try:
        # Try main resources first, then sidecar resources
        preview_path = PREVIEW_CACHE / f"filter_{filter_id}.jpg"
        if not preview_path.exists():
            preview_path = SIDECAR_PREVIEW_CACHE / f"filter_{filter_id}.jpg"
        
        if preview_path.exists():
            from fastapi.responses import FileResponse
            return FileResponse(preview_path)
        raise HTTPException(status_code=404, detail=f"Filter preview not found: {filter_id}")
    except Exception as e:
        logger.error(f"Error getting filter preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/preview/transition/{transition_id}")
async def get_transition_preview(transition_id: str):
    """Get transition preview"""
    try:
        # Try main resources first, then sidecar resources
        preview_path = PREVIEW_CACHE / f"transition_{transition_id}.gif"
        if not preview_path.exists():
            preview_path = SIDECAR_PREVIEW_CACHE / f"transition_{transition_id}.gif"
        
        if preview_path.exists():
            from fastapi.responses import FileResponse
            return FileResponse(preview_path)
        else:
            raise HTTPException(status_code=404, detail=f"Transition preview not found: {transition_id}")
    except Exception as e:
        logger.error(f"Error getting transition preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Orchestration functions

# Gemini-powered agentic orchestration
async def run_orchestration(session_id: str, request: PromptRequest):
    """Agentic orchestration loop using SclipBrain and Gemini 2.5 Pro"""
    try:
        # Create a send_message function for the brain
        async def send_message_wrapper(message):
            await manager.send_message(session_id, message)
        
        brain = SclipBrain(send_message_func=send_message_wrapper)
        # Start the agentic workflow (Gemini will plan and explain)
        async for message in brain.start_workflow_streaming(
            user_prompt=request.prompt,
            session_id=session_id,
            user_context={
                "style": request.style,
                "length": request.length,
                "tone": request.tone,
                "approval_mode": request.approval_mode,
                "quality_setting": request.quality_setting,
            }
        ):
            # Professional brain handles all messaging, just check for completion
            if message.get("type") == "completion":
                break
    except Exception as e:
        logger.error(f"Error in agentic orchestration for session {session_id}: {e}")
        update_session(session_id, {
            "status": "error",
            "errors": [str(e)]
        })
        await manager.send_message(session_id, {
            "type": "error",
            "message": f"Error during video creation: {str(e)}",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        })

async def continue_orchestration(session_id: str):
    """Continue orchestration after user approval"""
    # This would be implemented to continue from where it left off
    # after user approval or modification
    pass

async def handle_user_message(session_id: str, message: Dict[str, Any]):
    """Handle user message with TRUE AGENTIC AI integration using SclipBrain"""
    try:
        content = message.get("content", "")
        logger.info(f"Processing user message with SclipBrain: {content[:100]}...")
        
        # Create SclipBrain instance with proper message sending
        async def send_message_wrapper(msg):
            await manager.send_message(session_id, msg)
        
        # Initialize SclipBrain with the message sending function
        brain = SclipBrain(send_message_func=send_message_wrapper)
        
        # Get user context from the message or create default
        user_context = message.get("frontend_state", {}).get("userContext", {})
        if not user_context:
            user_context = {
                "style": "cinematic",
                "length": "medium", 
                "tone": "professional",
                "preferences": {}
            }
        
        # Start the TRUE AGENTIC WORKFLOW with streaming
        logger.info("Starting SclipBrain agentic workflow...")
        
        # Stream all messages from the agentic workflow
        async for agentic_message in brain.start_workflow_streaming(
            user_prompt=content,
            session_id=session_id,
            user_context=user_context
        ):
            # Send each message to the frontend
            await manager.send_message(session_id, agentic_message)
            
            # Handle completion
            if agentic_message.get("type") == "completion":
                logger.info("Agentic workflow completed")
                break
                
    except Exception as e:
        logger.error(f"Error in SclipBrain agentic workflow: {e}")
        await manager.send_message(session_id, {
            "type": "error",
            "message": f"Sorry, I encountered an error: {str(e)}",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        })

async def _send_gui_updates_for_tool(session_id: str, tool_name: str, result: Dict[str, Any]):
    """Send GUI updates based on tool execution result"""
    try:
        if tool_name == "script_writer" and result.get("script_text"):
            await manager.send_message(session_id, {
                "type": "gui_update",
                "update_type": "script_created",
                "data": {
                    "script_content": result["script_text"]
                },
                "timestamp": datetime.now().isoformat()
            })
        
        elif tool_name == "broll_finder" and result.get("downloaded_files"):
            await manager.send_message(session_id, {
                "type": "gui_update",
                "update_type": "media_downloaded",
                "data": {
                    "media_files": result["downloaded_files"]
                },
                "timestamp": datetime.now().isoformat()
            })
        
        elif tool_name == "voiceover_generator" and result.get("audio_path"):
            await manager.send_message(session_id, {
                "type": "gui_update",
                "update_type": "voiceover_created",
                "data": {
                    "audio_path": result["audio_path"]
                },
                "timestamp": datetime.now().isoformat()
            })
        
        elif tool_name == "video_processor" and result.get("video_path"):
            await manager.send_message(session_id, {
                "type": "gui_update",
                "update_type": "video_created",
                "data": {
                    "video_path": result["video_path"],
                    "thumbnail": result.get("thumbnail")
                },
                "timestamp": datetime.now().isoformat()
            })
    
    except Exception as e:
        logger.error(f"Error sending GUI updates for tool {tool_name}: {e}")

# Error handlers
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    """Handle Pydantic validation errors"""
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": exc.errors()}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

@app.on_event("startup")
async def start_cleanup_job():
    """Start background cleanup job and initialize AI agent"""
    global true_ai_agent
    
    # Initialize True AI Agent (but we'll use SclipBrain directly now)
    try:
        # Create a simple AI service wrapper for TrueAIAgent if needed
        class SimpleAIService:
            async def generate_response(self, prompt: str) -> str:
                # Use the existing SclipBrain's AI response method
                from app.orchestrator.sclip_brain import SclipBrain
                brain = SclipBrain()
                return await brain._get_ai_response(prompt)
        
        true_ai_agent = TrueAIAgent(SimpleAIService(), manager)
        logger.info("True AI Agent initialized with RAG and MCP integration")
    except Exception as e:
        logger.error(f"Failed to initialize True AI Agent: {e}")
        true_ai_agent = None

    async def cleanup_old_files():
        """Clean up old temporary files"""
        while True:
            try:
                # Clean up files older than 24 hours
                cutoff_time = datetime.now() - timedelta(hours=24)
                
                # Clean up temp directory
                temp_dir = Path("temp")
                if temp_dir.exists():
                    for file_path in temp_dir.rglob("*"):
                        if file_path.is_file():
                            file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                            if file_time < cutoff_time:
                                try:
                                    file_path.unlink()
                                    logger.debug(f"Cleaned up old file: {file_path}")
                                except Exception as e:
                                    logger.debug(f"Could not delete {file_path}: {e}")
                
                # Clean up downloads directory
                downloads_dir = Path("downloads")
                if downloads_dir.exists():
                    for file_path in downloads_dir.rglob("*"):
                        if file_path.is_file():
                            file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                            if file_time < cutoff_time:
                                try:
                                    file_path.unlink()
                                    logger.debug(f"Cleaned up old download: {file_path}")
                                except Exception as e:
                                    logger.debug(f"Could not delete {file_path}: {e}")
                
            except Exception as e:
                logger.error(f"Error in cleanup job: {e}")
            
            # Run cleanup every hour
            await asyncio.sleep(3600)
    
    # Start cleanup job
    asyncio.create_task(cleanup_old_files())

@app.post("/api/update-script")
async def update_script(request: Request):
    """Update script content for a session"""
    try:
        data = await request.json()
        session_id = data.get("session_id")
        script_content = data.get("script_content")
        
        if not session_id or script_content is None:
            raise HTTPException(status_code=400, detail="Missing session_id or script_content")
        
        # Update the AI agent's context with the new script
        if hasattr(manager, 'professional_handler') and session_id in manager.professional_handler.agents:
            agent = manager.professional_handler.agents[session_id]
            agent.context.current_project["script"] = script_content
            logger.info(f"Updated script for session {session_id}")
        
        return {"success": True, "message": "Script updated successfully"}
        
    except Exception as e:
        logger.error(f"Error updating script: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Project management
PROJECTS_DIR = Path.home() / "Videos" / "Sclip" / "Projects"
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

def get_project_path(project_id: str) -> Path:
    """Get the path for a specific project"""
    return PROJECTS_DIR / project_id

def create_project_structure(project_path: Path) -> None:
    """Create the standard folder structure for a project"""
    (project_path / "resources" / "broll").mkdir(parents=True, exist_ok=True)
    (project_path / "resources" / "scripts").mkdir(parents=True, exist_ok=True)
    (project_path / "resources" / "voiceovers").mkdir(parents=True, exist_ok=True)
    (project_path / "resources" / "images").mkdir(parents=True, exist_ok=True)
    (project_path / "resources" / "audio").mkdir(parents=True, exist_ok=True)
    (project_path / "resources" / "videos").mkdir(parents=True, exist_ok=True)
    (project_path / "exports").mkdir(parents=True, exist_ok=True)
    (project_path / "temp").mkdir(parents=True, exist_ok=True)

def get_project_info(project_path: Path) -> Dict[str, Any]:
    """Get project information from project.json"""
    project_json = project_path / "project.json"
    if project_json.exists():
        with open(project_json, 'r') as f:
            return json.load(f)
    return {}

def save_project_info(project_path: Path, info: Dict[str, Any]) -> None:
    """Save project information to project.json"""
    project_json = project_path / "project.json"
    with open(project_json, 'w') as f:
        json.dump(info, f, indent=2, default=str)

def calculate_project_size(project_path: Path) -> int:
    """Calculate the total size of a project in bytes"""
    total_size = 0
    for root, dirs, files in os.walk(project_path):
        for file in files:
            file_path = Path(root) / file
            if file_path.exists():
                total_size += file_path.stat().st_size
    return total_size

@app.get("/api/projects")
async def get_projects():
    """Get all projects"""
    try:
        projects = []
        if PROJECTS_DIR.exists():
            for project_dir in PROJECTS_DIR.iterdir():
                if project_dir.is_dir():
                    project_info = get_project_info(project_dir)
                    if project_info:
                        # Calculate project size
                        size_bytes = calculate_project_size(project_dir)
                        size_mb = round(size_bytes / (1024 * 1024), 2)
                        
                        projects.append({
                            "id": project_dir.name,
                            "name": project_info.get("name", "Untitled Project"),
                            "path": str(project_dir),
                            "createdAt": project_info.get("createdAt", ""),
                            "lastModified": project_info.get("lastModified", ""),
                            "status": project_info.get("status", "active"),
                            "size": size_mb,
                            "thumbnail": project_info.get("thumbnail")
                        })
        
        # Sort by last modified date
        projects.sort(key=lambda x: x["lastModified"], reverse=True)
        return projects
    except Exception as e:
        logger.error(f"Error getting projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects")
async def create_project(request: Request):
    """Create a new project"""
    try:
        data = await request.json()
        project_name = data.get("name", "Untitled Project")
        
        # Generate unique project ID
        project_id = str(uuid.uuid4())
        project_path = get_project_path(project_id)
        
        # Create project structure
        create_project_structure(project_path)
        
        # Create project info
        project_info = {
            "id": project_id,
            "name": project_name,
            "createdAt": datetime.now().isoformat(),
            "lastModified": datetime.now().isoformat(),
            "status": "active",
            "version": "1.0.0"
        }
        
        # Save project info
        save_project_info(project_path, project_info)
        
        logger.info(f"Created new project: {project_name} ({project_id})")
        
        return {
            "id": project_id,
            "name": project_name,
            "path": str(project_path),
            "createdAt": project_info["createdAt"],
            "lastModified": project_info["lastModified"],
            "status": "active",
            "size": 0
        }
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    """Get a specific project"""
    try:
        project_path = get_project_path(project_id)
        if not project_path.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        
        project_info = get_project_info(project_path)
        if not project_info:
            raise HTTPException(status_code=404, detail="Project info not found")
        
        # Calculate project size
        size_bytes = calculate_project_size(project_path)
        size_mb = round(size_bytes / (1024 * 1024), 2)
        
        return {
            "id": project_id,
            "name": project_info.get("name", "Untitled Project"),
            "path": str(project_path),
            "createdAt": project_info.get("createdAt", ""),
            "lastModified": project_info.get("lastModified", ""),
            "status": project_info.get("status", "active"),
            "size": size_mb,
            "thumbnail": project_info.get("thumbnail")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/projects/{project_id}")
async def update_project(project_id: str, request: Request):
    """Update a project"""
    try:
        project_path = get_project_path(project_id)
        if not project_path.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        
        data = await request.json()
        project_info = get_project_info(project_path)
        
        # Update fields
        if "name" in data:
            project_info["name"] = data["name"]
        if "status" in data:
            project_info["status"] = data["status"]
        
        project_info["lastModified"] = datetime.now().isoformat()
        
        # Save updated info
        save_project_info(project_path, project_info)
        
        logger.info(f"Updated project {project_id}")
        
        return {"success": True, "message": "Project updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project"""
    try:
        project_path = get_project_path(project_id)
        if not project_path.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Remove the entire project directory
        shutil.rmtree(project_path)
        
        logger.info(f"Deleted project {project_id}")
        
        return {"success": True, "message": "Project deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_id}/files")
async def get_project_files(project_id: str, type: Optional[str] = None):
    """Get files in a project"""
    try:
        project_path = get_project_path(project_id)
        if not project_path.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        
        resources_path = project_path / "resources"
        files = []
        
        if resources_path.exists():
            for root, dirs, filenames in os.walk(resources_path):
                for filename in filenames:
                    file_path = Path(root) / filename
                    relative_path = file_path.relative_to(resources_path)
                    
                    # Determine file type
                    file_type = "unknown"
                    if filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                        file_type = "video"
                    elif filename.lower().endswith(('.mp3', '.wav', '.aac', '.flac')):
                        file_type = "audio"
                    elif filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                        file_type = "image"
                    elif filename.lower().endswith(('.txt', '.md', '.doc', '.docx')):
                        file_type = "document"
                    
                    # Filter by type if specified
                    if type and file_type != type:
                        continue
                    
                    file_stat = file_path.stat()
                    files.append({
                        "name": filename,
                        "path": str(relative_path),
                        "fullPath": str(file_path),
                        "type": file_type,
                        "size": file_stat.st_size,
                        "sizeMB": round(file_stat.st_size / (1024 * 1024), 2),
                        "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                        "folder": str(relative_path.parent)
                    })
        
        # Sort by modified date
        files.sort(key=lambda x: x["modified"], reverse=True)
        
        return files
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project files for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_id}/broll/{filename:path}")
async def serve_broll_image(project_id: str, filename: str):
    """Serve B-roll images from project resources"""
    try:
        project_path = get_project_path(project_id)
        if not project_path.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Construct the file path
        file_path = project_path / "resources" / "broll" / filename
        
        # Security check: ensure the file is within the project's broll directory
        try:
            file_path.resolve().relative_to(project_path / "resources" / "broll")
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Determine MIME type
        mime_type = "image/jpeg"  # Default
        if filename.lower().endswith('.png'):
            mime_type = "image/png"
        elif filename.lower().endswith('.gif'):
            mime_type = "image/gif"
        elif filename.lower().endswith('.bmp'):
            mime_type = "image/bmp"
        elif filename.lower().endswith('.webp'):
            mime_type = "image/webp"
        
        return FileResponse(
            path=file_path,
            media_type=mime_type,
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving B-roll image {filename} for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_id}/files/{filename:path}")
async def serve_project_file(project_id: str, filename: str):
    """Serve any file from project resources"""
    try:
        project_path = get_project_path(project_id)
        if not project_path.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Construct the file path
        file_path = project_path / "resources" / filename
        
        # Security check: ensure the file is within the project's resources directory
        try:
            file_path.resolve().relative_to(project_path / "resources")
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Determine MIME type based on file extension
        mime_type = "application/octet-stream"  # Default
        if filename.lower().endswith(('.jpg', '.jpeg')):
            mime_type = "image/jpeg"
        elif filename.lower().endswith('.png'):
            mime_type = "image/png"
        elif filename.lower().endswith('.gif'):
            mime_type = "image/gif"
        elif filename.lower().endswith('.bmp'):
            mime_type = "image/bmp"
        elif filename.lower().endswith('.webp'):
            mime_type = "image/webp"
        elif filename.lower().endswith('.mp4'):
            mime_type = "video/mp4"
        elif filename.lower().endswith('.avi'):
            mime_type = "video/x-msvideo"
        elif filename.lower().endswith('.mov'):
            mime_type = "video/quicktime"
        elif filename.lower().endswith('.mkv'):
            mime_type = "video/x-matroska"
        elif filename.lower().endswith('.mp3'):
            mime_type = "audio/mpeg"
        elif filename.lower().endswith('.wav'):
            mime_type = "audio/wav"
        elif filename.lower().endswith('.aac'):
            mime_type = "audio/aac"
        elif filename.lower().endswith('.flac'):
            mime_type = "audio/flac"
        
        return FileResponse(
            path=file_path,
            media_type=mime_type,
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving project file {filename} for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rag/statistics")
async def get_rag_statistics():
    """Get RAG system statistics"""
    try:
        stats = await rag_service.get_statistics()
        return {"success": True, "statistics": stats}
    except Exception as e:
        logger.error(f"Error getting RAG statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/mcp/statistics")
async def get_mcp_statistics():
    """Get MCP system statistics"""
    try:
        stats = await enhanced_mcp.get_statistics()
        return {"success": True, "statistics": stats}
    except Exception as e:
        logger.error(f"Error getting MCP statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/mcp/tools")
async def get_available_tools(query: str = None):
    """Get available tools (with optional query for discovery)"""
    try:
        if query:
            tools = await enhanced_mcp.discover_tools(query)
        else:
            tools = list(enhanced_mcp.tools.values())
        
        return {"success": True, "tools": [tool.__dict__ for tool in tools]}
    except Exception as e:
        logger.error(f"Error getting tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rag/search")
async def search_rag(query: str = Body(..., embed=True), top_k: int = Body(5, embed=True)):
    """Search RAG system"""
    try:
        results = await rag_service.search(query, top_k)
        return {"success": True, "results": [result.__dict__ for result in results]}
    except Exception as e:
        logger.error(f"Error searching RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rag/add-document")
async def add_document_to_rag(content: str = Body(..., embed=True), metadata: Dict[str, Any] = Body({}, embed=True)):
    """Add document to RAG system"""
    try:
        doc_id = await rag_service.add_document(content, metadata)
        return {"success": True, "document_id": doc_id}
    except Exception as e:
        logger.error(f"Error adding document to RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 