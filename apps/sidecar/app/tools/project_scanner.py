"""
Project Scanner Tool
Allows the AI brain to read and analyze project files, scripts, and current state
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base_tool import BaseTool, ToolStatus, ToolError
from ..utils.logger import get_logger

logger = get_logger(__name__)

class ProjectScannerTool(BaseTool):
    """Tool for scanning and reading project files and state"""
    
    def __init__(self):
        super().__init__(
            name="project_scanner",
            description="Scan and read project files, scripts, and current state"
        )
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "scan_type": {
                    "type": "string",
                    "enum": ["script", "media", "voiceover", "video", "project_state", "all"],
                    "description": "What to scan/read"
                },
                "project_id": {
                    "type": "string",
                    "description": "Project ID to scan"
                },
                "file_path": {
                    "type": "string",
                    "description": "Specific file path to read (optional)"
                },
                "include_metadata": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include file metadata"
                }
            },
            "required": ["scan_type", "project_id"]
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "scan_type": {"type": "string"},
                "project_id": {"type": "string"},
                "content": {"type": "object"},
                "metadata": {"type": "object"},
                "file_count": {"type": "integer"},
                "total_size": {"type": "integer"},
                "last_modified": {"type": "string"},
                "error": {"type": "string"}
            }
        }
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Scan and read project files"""
        try:
            scan_type = input_data.get("scan_type", "all")
            project_id = input_data.get("project_id")
            file_path = input_data.get("file_path")
            include_metadata = input_data.get("include_metadata", True)
            
            if not project_id:
                raise ToolError("Project ID is required")
            
            # Build project path
            project_path = Path.home() / "Videos" / "Sclip" / "Projects" / project_id
            
            if not project_path.exists():
                return {
                    "success": False,
                    "error": f"Project {project_id} not found",
                    "scan_type": scan_type,
                    "project_id": project_id
                }
            
            result = {
                "success": True,
                "scan_type": scan_type,
                "project_id": project_id,
                "content": {},
                "metadata": {},
                "file_count": 0,
                "total_size": 0,
                "last_modified": datetime.now().isoformat()
            }
            
            if scan_type == "script" or scan_type == "all":
                script_content = await self._read_script(project_path)
                result["content"]["script"] = script_content
            
            if scan_type == "media" or scan_type == "all":
                media_info = await self._scan_media(project_path, include_metadata)
                result["content"]["media"] = media_info["files"]
                result["metadata"]["media"] = media_info["metadata"]
                result["file_count"] += media_info["file_count"]
                result["total_size"] += media_info["total_size"]
            
            if scan_type == "voiceover" or scan_type == "all":
                voiceover_info = await self._scan_voiceover(project_path, include_metadata)
                result["content"]["voiceover"] = voiceover_info["files"]
                result["metadata"]["voiceover"] = voiceover_info["metadata"]
                result["file_count"] += voiceover_info["file_count"]
                result["total_size"] += voiceover_info["total_size"]
            
            if scan_type == "video" or scan_type == "all":
                video_info = await self._scan_videos(project_path, include_metadata)
                result["content"]["videos"] = video_info["files"]
                result["metadata"]["videos"] = video_info["metadata"]
                result["file_count"] += video_info["file_count"]
                result["total_size"] += video_info["total_size"]
            
            if scan_type == "project_state" or scan_type == "all":
                project_state = await self._read_project_state(project_path)
                result["content"]["project_state"] = project_state
            
            # If specific file path provided, read that file
            if file_path:
                file_content = await self._read_specific_file(project_path, file_path)
                result["content"]["specific_file"] = file_content
            
            logger.info(f"Project scan completed for {project_id}, type: {scan_type}")
            return result
            
        except Exception as e:
            logger.error(f"Error scanning project: {e}")
            return {
                "success": False,
                "error": str(e),
                "scan_type": scan_type,
                "project_id": project_id
            }
    
    async def _read_script(self, project_path: Path) -> Dict[str, Any]:
        """Read script content"""
        script_file = project_path / "script.txt"
        script_json = project_path / "script.json"
        
        script_content = {
            "text": "",
            "metadata": {},
            "exists": False
        }
        
        # Try reading script.txt first
        if script_file.exists():
            try:
                with open(script_file, 'r', encoding='utf-8') as f:
                    script_content["text"] = f.read()
                script_content["exists"] = True
                script_content["source"] = "script.txt"
            except Exception as e:
                logger.warning(f"Error reading script.txt: {e}")
        
        # Try reading script.json
        elif script_json.exists():
            try:
                with open(script_json, 'r', encoding='utf-8') as f:
                    script_data = json.load(f)
                    script_content["text"] = script_data.get("content", "")
                    script_content["metadata"] = script_data
                script_content["exists"] = True
                script_content["source"] = "script.json"
            except Exception as e:
                logger.warning(f"Error reading script.json: {e}")
        
        return script_content
    
    async def _scan_media(self, project_path: Path, include_metadata: bool) -> Dict[str, Any]:
        """Scan media files (B-roll)"""
        media_path = project_path / "resources" / "broll"
        
        files = []
        metadata = {
            "total_files": 0,
            "image_count": 0,
            "video_count": 0,
            "total_size": 0,
            "file_types": {}
        }
        
        if media_path.exists():
            for file_path in media_path.rglob("*"):
                if file_path.is_file():
                    file_info = {
                        "name": file_path.name,
                        "path": str(file_path),
                        "size": file_path.stat().st_size,
                        "type": self._get_file_type(file_path),
                        "extension": file_path.suffix.lower(),
                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    }
                    
                    if include_metadata:
                        file_info["metadata"] = await self._get_file_metadata(file_path)
                    
                    files.append(file_info)
                    
                    # Update metadata
                    metadata["total_files"] += 1
                    metadata["total_size"] += file_info["size"]
                    
                    if file_info["type"] == "image":
                        metadata["image_count"] += 1
                    elif file_info["type"] == "video":
                        metadata["video_count"] += 1
                    
                    ext = file_info["extension"]
                    metadata["file_types"][ext] = metadata["file_types"].get(ext, 0) + 1
        
        return {
            "files": files,
            "metadata": metadata,
            "file_count": len(files),
            "total_size": metadata["total_size"]
        }
    
    async def _scan_voiceover(self, project_path: Path, include_metadata: bool) -> Dict[str, Any]:
        """Scan voiceover files"""
        voiceover_path = project_path / "resources" / "voiceover"
        
        files = []
        metadata = {
            "total_files": 0,
            "total_size": 0,
            "file_types": {}
        }
        
        if voiceover_path.exists():
            for file_path in voiceover_path.rglob("*"):
                if file_path.is_file():
                    file_info = {
                        "name": file_path.name,
                        "path": str(file_path),
                        "size": file_path.stat().st_size,
                        "type": "audio",
                        "extension": file_path.suffix.lower(),
                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    }
                    
                    if include_metadata:
                        file_info["metadata"] = await self._get_file_metadata(file_path)
                    
                    files.append(file_info)
                    
                    # Update metadata
                    metadata["total_files"] += 1
                    metadata["total_size"] += file_info["size"]
                    
                    ext = file_info["extension"]
                    metadata["file_types"][ext] = metadata["file_types"].get(ext, 0) + 1
        
        return {
            "files": files,
            "metadata": metadata,
            "file_count": len(files),
            "total_size": metadata["total_size"]
        }
    
    async def _scan_videos(self, project_path: Path, include_metadata: bool) -> Dict[str, Any]:
        """Scan video files"""
        video_path = project_path / "output"
        
        files = []
        metadata = {
            "total_files": 0,
            "total_size": 0,
            "file_types": {}
        }
        
        if video_path.exists():
            for file_path in video_path.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']:
                    file_info = {
                        "name": file_path.name,
                        "path": str(file_path),
                        "size": file_path.stat().st_size,
                        "type": "video",
                        "extension": file_path.suffix.lower(),
                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    }
                    
                    if include_metadata:
                        file_info["metadata"] = await self._get_file_metadata(file_path)
                    
                    files.append(file_info)
                    
                    # Update metadata
                    metadata["total_files"] += 1
                    metadata["total_size"] += file_info["size"]
                    
                    ext = file_info["extension"]
                    metadata["file_types"][ext] = metadata["file_types"].get(ext, 0) + 1
        
        return {
            "files": files,
            "metadata": metadata,
            "file_count": len(files),
            "total_size": metadata["total_size"]
        }
    
    async def _read_project_state(self, project_path: Path) -> Dict[str, Any]:
        """Read project state and configuration"""
        state_file = project_path / "project_state.json"
        config_file = project_path / "config.json"
        
        project_state = {
            "project_id": project_path.name,
            "created": None,
            "modified": None,
            "status": "unknown",
            "config": {},
            "state": {}
        }
        
        # Read project state
        if state_file.exists():
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    project_state["state"] = json.load(f)
            except Exception as e:
                logger.warning(f"Error reading project state: {e}")
        
        # Read config
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    project_state["config"] = json.load(f)
            except Exception as e:
                logger.warning(f"Error reading project config: {e}")
        
        # Get file system info
        project_state["created"] = datetime.fromtimestamp(project_path.stat().st_ctime).isoformat()
        project_state["modified"] = datetime.fromtimestamp(project_path.stat().st_mtime).isoformat()
        
        return project_state
    
    async def _read_specific_file(self, project_path: Path, file_path: str) -> Dict[str, Any]:
        """Read a specific file"""
        full_path = project_path / file_path
        
        if not full_path.exists():
            return {
                "exists": False,
                "error": f"File {file_path} not found"
            }
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "exists": True,
                "path": str(full_path),
                "content": content,
                "size": full_path.stat().st_size,
                "modified": datetime.fromtimestamp(full_path.stat().st_mtime).isoformat()
            }
        except Exception as e:
            return {
                "exists": False,
                "error": f"Error reading file: {e}"
            }
    
    def _get_file_type(self, file_path: Path) -> str:
        """Determine file type based on extension"""
        ext = file_path.suffix.lower()
        
        image_exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']
        video_exts = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
        audio_exts = ['.mp3', '.wav', '.aac', '.ogg', '.flac', '.m4a']
        
        if ext in image_exts:
            return "image"
        elif ext in video_exts:
            return "video"
        elif ext in audio_exts:
            return "audio"
        else:
            return "unknown"
    
    async def _get_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Get additional file metadata"""
        try:
            stat = file_path.stat()
            return {
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "permissions": oct(stat.st_mode)[-3:]
            }
        except Exception as e:
            logger.warning(f"Error getting file metadata: {e}")
            return {} 