"""
Video Viewer Tool
Allows the AI brain to analyze and get information about video files
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base_tool import BaseTool, ToolStatus, ToolError
from ..utils.logger import get_logger

logger = get_logger(__name__)

class VideoViewerTool(BaseTool):
    """Tool for viewing and analyzing video files"""
    
    def __init__(self):
        super().__init__(
            name="video_viewer",
            description="View and analyze video files"
        )
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "video_path": {
                    "type": "string",
                    "description": "Path to the video file"
                },
                "project_id": {
                    "type": "string",
                    "description": "Project ID (if video is in project)"
                },
                "analysis_type": {
                    "type": "string",
                    "enum": ["metadata", "thumbnail", "preview", "info", "all"],
                    "default": "all",
                    "description": "Type of analysis to perform"
                },
                "generate_thumbnail": {
                    "type": "boolean",
                    "default": False,
                    "description": "Generate thumbnail image"
                }
            },
            "required": ["video_path"]
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "video_path": {"type": "string"},
                "exists": {"type": "boolean"},
                "metadata": {"type": "object"},
                "info": {"type": "object"},
                "thumbnail_path": {"type": "string"},
                "preview_url": {"type": "string"},
                "error": {"type": "string"}
            }
        }
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """View and analyze video file"""
        try:
            video_path = input_data.get("video_path")
            project_id = input_data.get("project_id")
            analysis_type = input_data.get("analysis_type", "all")
            generate_thumbnail = input_data.get("generate_thumbnail", False)
            
            if not video_path:
                raise ToolError("Video path is required")
            
            # Resolve video path
            resolved_path = await self._resolve_video_path(video_path, project_id)
            
            if not resolved_path.exists():
                return {
                    "success": False,
                    "video_path": video_path,
                    "exists": False,
                    "error": f"Video file not found: {video_path}"
                }
            
            result = {
                "success": True,
                "video_path": str(resolved_path),
                "exists": True,
                "metadata": {},
                "info": {},
                "thumbnail_path": None,
                "preview_url": None
            }
            
            # Get basic file info
            if analysis_type in ["info", "all"]:
                result["info"] = await self._get_video_info(resolved_path)
            
            # Get video metadata
            if analysis_type in ["metadata", "all"]:
                result["metadata"] = await self._get_video_metadata(resolved_path)
            
            # Generate thumbnail
            if generate_thumbnail and analysis_type in ["thumbnail", "all"]:
                thumbnail_path = await self._generate_thumbnail(resolved_path, project_id)
                result["thumbnail_path"] = thumbnail_path
            
            # Create preview URL
            if project_id:
                result["preview_url"] = f"http://127.0.0.1:8001/api/projects/{project_id}/video/{resolved_path.name}"
            
            logger.info(f"Video analysis completed for {resolved_path}")
            return result
            
        except Exception as e:
            logger.error(f"Error viewing video: {e}")
            return {
                "success": False,
                "video_path": video_path,
                "exists": False,
                "error": str(e)
            }
    
    async def _resolve_video_path(self, video_path: str, project_id: Optional[str] = None) -> Path:
        """Resolve video path to absolute path"""
        path = Path(video_path)
        
        # If it's already an absolute path, return it
        if path.is_absolute():
            return path
        
        # If project_id is provided, try to find in project
        if project_id:
            project_video_path = Path.home() / "Videos" / "Sclip" / "Projects" / project_id / "output" / path.name
            if project_video_path.exists():
                return project_video_path
            
            # Try in resources/videos
            project_video_path = Path.home() / "Videos" / "Sclip" / "Projects" / project_id / "resources" / "videos" / path.name
            if project_video_path.exists():
                return project_video_path
        
        # Try relative to current working directory
        cwd_path = Path.cwd() / path
        if cwd_path.exists():
            return cwd_path
        
        # Return the original path (will be checked for existence later)
        return path
    
    async def _get_video_info(self, video_path: Path) -> Dict[str, Any]:
        """Get basic video file information"""
        try:
            stat = video_path.stat()
            
            return {
                "name": video_path.name,
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "size_gb": round(stat.st_size / (1024 * 1024 * 1024), 2),
                "extension": video_path.suffix.lower(),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "permissions": oct(stat.st_mode)[-3:],
                "path": str(video_path)
            }
        except Exception as e:
            logger.warning(f"Error getting video info: {e}")
            return {"error": str(e)}
    
    async def _get_video_metadata(self, video_path: Path) -> Dict[str, Any]:
        """Get video metadata using ffprobe"""
        try:
            import subprocess
            import json
            
            # Use ffprobe to get video metadata
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(video_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                metadata = json.loads(result.stdout)
                
                # Extract key information
                format_info = metadata.get("format", {})
                streams = metadata.get("streams", [])
                
                # Find video and audio streams
                video_stream = None
                audio_stream = None
                
                for stream in streams:
                    if stream.get("codec_type") == "video":
                        video_stream = stream
                    elif stream.get("codec_type") == "audio":
                        audio_stream = stream
                
                return {
                    "format": {
                        "format_name": format_info.get("format_name"),
                        "duration": format_info.get("duration"),
                        "bit_rate": format_info.get("bit_rate"),
                        "size": format_info.get("size")
                    },
                    "video_stream": {
                        "codec": video_stream.get("codec_name") if video_stream else None,
                        "width": video_stream.get("width") if video_stream else None,
                        "height": video_stream.get("height") if video_stream else None,
                        "fps": video_stream.get("r_frame_rate") if video_stream else None,
                        "bit_rate": video_stream.get("bit_rate") if video_stream else None
                    },
                    "audio_stream": {
                        "codec": audio_stream.get("codec_name") if audio_stream else None,
                        "sample_rate": audio_stream.get("sample_rate") if audio_stream else None,
                        "channels": audio_stream.get("channels") if audio_stream else None,
                        "bit_rate": audio_stream.get("bit_rate") if audio_stream else None
                    },
                    "raw_metadata": metadata
                }
            else:
                return {
                    "error": f"ffprobe failed: {result.stderr}",
                    "raw_output": result.stdout,
                    "raw_error": result.stderr
                }
                
        except ImportError:
            return {
                "error": "ffprobe not available - install ffmpeg for video metadata"
            }
        except Exception as e:
            logger.warning(f"Error getting video metadata: {e}")
            return {"error": str(e)}
    
    async def _generate_thumbnail(self, video_path: Path, project_id: Optional[str] = None) -> Optional[str]:
        """Generate thumbnail from video"""
        try:
            import subprocess
            
            # Create thumbnails directory
            if project_id:
                thumb_dir = Path.home() / "Videos" / "Sclip" / "Projects" / project_id / "thumbnails"
            else:
                thumb_dir = video_path.parent / "thumbnails"
            
            thumb_dir.mkdir(exist_ok=True)
            
            # Generate thumbnail filename
            thumb_name = f"{video_path.stem}_thumb.jpg"
            thumb_path = thumb_dir / thumb_name
            
            # Use ffmpeg to generate thumbnail
            cmd = [
                "ffmpeg",
                "-i", str(video_path),
                "-ss", "00:00:05",  # Take frame at 5 seconds
                "-vframes", "1",
                "-q:v", "2",  # High quality
                "-y",  # Overwrite if exists
                str(thumb_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and thumb_path.exists():
                return str(thumb_path)
            else:
                logger.warning(f"Failed to generate thumbnail: {result.stderr}")
                return None
                
        except ImportError:
            logger.warning("ffmpeg not available - cannot generate thumbnail")
            return None
        except Exception as e:
            logger.warning(f"Error generating thumbnail: {e}")
            return None 