"""
Media Downloader Service for Sclip
Handles concurrent downloads, file processing, and session-based organization
"""

import asyncio
import aiohttp
import aiofiles
import os
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse
import time
import json
from PIL import Image
import subprocess

from ..utils.logger import get_logger

logger = get_logger(__name__)

class MediaDownloaderService:
    """
    Media downloader service with concurrent downloads, progress tracking, and file processing
    Provides comprehensive media download capabilities for B-roll finder
    """
    
    def __init__(self):
        self.max_concurrent_downloads = 5
        self.download_timeout = 30  # seconds
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        self.retry_attempts = 3
        self.retry_delay = 1  # seconds
        
        # Download queue and progress tracking
        self.download_queue = asyncio.Queue()
        self.active_downloads = {}
        self.download_history = {}
        
        # File processing settings
        self.supported_image_formats = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        self.supported_video_formats = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv'}
        self.supported_audio_formats = {'.mp3', '.wav', '.aac', '.ogg', '.flac'}
        
        # Storage quotas
        self.max_storage_per_session = 1 * 1024 * 1024 * 1024  # 1GB
        self.session_storage_usage = {}
        
        logger.info("Media Downloader Service initialized")
    
    def _generate_file_hash(self, url: str, content: bytes) -> str:
        """Generate hash for file content"""
        return hashlib.md5(content).hexdigest()
    
    def _get_file_extension(self, url: str, content_type: str = None) -> str:
        """Get file extension from URL or content type"""
        # Try URL first
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        
        # Extract extension from path
        if '.' in path:
            ext = '.' + path.split('.')[-1]
            if ext in self.supported_image_formats | self.supported_video_formats | self.supported_audio_formats:
                return ext
        
        # Try content type
        if content_type:
            if 'image/' in content_type:
                if 'jpeg' in content_type:
                    return '.jpg'
                elif 'png' in content_type:
                    return '.png'
                elif 'gif' in content_type:
                    return '.gif'
                elif 'webp' in content_type:
                    return '.webp'
            elif 'video/' in content_type:
                if 'mp4' in content_type:
                    return '.mp4'
                elif 'webm' in content_type:
                    return '.webm'
            elif 'audio/' in content_type:
                if 'mpeg' in content_type:
                    return '.mp3'
                elif 'wav' in content_type:
                    return '.wav'
        
        # Default to .jpg for images, .mp4 for videos
        return '.jpg'
    
    def _get_media_type(self, file_extension: str) -> str:
        """Determine media type from file extension"""
        if file_extension in self.supported_image_formats:
            return "image"
        elif file_extension in self.supported_video_formats:
            return "video"
        elif file_extension in self.supported_audio_formats:
            return "audio"
        else:
            return "unknown"
    
    async def _download_file(self, url: str, session_id: str, filename: str = None) -> Dict[str, Any]:
        """Download a single file with retry logic"""
        for attempt in range(self.retry_attempts):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.download_timeout)) as session:
                    async with session.get(url) as response:
                        if response.status != 200:
                            logger.error(f"Download failed for {url}: HTTP {response.status}")
                            continue
                        
                        # Check file size
                        content_length = response.headers.get('content-length')
                        if content_length and int(content_length) > self.max_file_size:
                            logger.error(f"File too large: {url} ({content_length} bytes)")
                            return {"error": "File too large"}
                        
                        # Read content
                        content = await response.read()
                        
                        # Generate filename if not provided
                        if not filename:
                            content_type = response.headers.get('content-type', '')
                            extension = self._get_file_extension(url, content_type)
                            file_hash = self._generate_file_hash(url, content)
                            filename = f"{file_hash}{extension}"
                        
                        # Create session directory
                        session_dir = Path(f"sessions/{session_id}/downloads")
                        session_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Save file
                        file_path = session_dir / filename
                        async with aiofiles.open(file_path, 'wb') as f:
                            await f.write(content)
                        
                        # Get file info
                        file_size = len(content)
                        file_extension = Path(filename).suffix.lower()
                        media_type = self._get_media_type(file_extension)
                        
                        # Update storage usage
                        self.session_storage_usage[session_id] = self.session_storage_usage.get(session_id, 0) + file_size
                        
                        logger.info(f"Downloaded {filename} ({file_size} bytes) to {file_path}")
                        
                        return {
                            "success": True,
                            "file_path": str(file_path),
                            "filename": filename,
                            "file_size": file_size,
                            "media_type": media_type,
                            "extension": file_extension,
                            "url": url
                        }
                        
            except asyncio.TimeoutError:
                logger.warning(f"Download timeout for {url} (attempt {attempt + 1})")
            except Exception as e:
                logger.error(f"Download error for {url} (attempt {attempt + 1}): {e}")
            
            if attempt < self.retry_attempts - 1:
                await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        return {"error": f"Failed to download after {self.retry_attempts} attempts"}
    
    async def _process_image(self, file_path: str) -> Dict[str, Any]:
        """Process downloaded image file"""
        try:
            with Image.open(file_path) as img:
                # Get image info
                width, height = img.size
                format_name = img.format
                mode = img.mode
                
                # Generate thumbnail
                thumbnail_path = str(file_path).replace('.', '_thumb.')
                img.thumbnail((320, 240))
                img.save(thumbnail_path)
                
                return {
                    "width": width,
                    "height": height,
                    "format": format_name,
                    "mode": mode,
                    "thumbnail_path": thumbnail_path
                }
                
        except Exception as e:
            logger.error(f"Error processing image {file_path}: {e}")
            return {"error": str(e)}
    
    async def _process_video(self, file_path: str) -> Dict[str, Any]:
        """Process downloaded video file"""
        try:
            # Use FFprobe to get video info
            cmd = [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", "-show_streams", file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return {"error": "Failed to get video info"}
            
            video_info = json.loads(result.stdout)
            
            # Extract relevant info
            format_info = video_info.get("format", {})
            video_stream = next((s for s in video_info.get("streams", []) if s.get("codec_type") == "video"), {})
            audio_stream = next((s for s in video_info.get("streams", []) if s.get("codec_type") == "audio"), {})
            
            # Generate thumbnail
            thumbnail_path = str(file_path).replace('.', '_thumb.')
            thumb_cmd = [
                "ffmpeg", "-y", "-i", file_path,
                "-ss", "00:00:01", "-vframes", "1",
                "-vf", "scale=320:240:flags=lanczos",
                thumbnail_path
            ]
            
            subprocess.run(thumb_cmd, capture_output=True)
            
            return {
                "duration": float(format_info.get("duration", 0)),
                "width": int(video_stream.get("width", 0)),
                "height": int(video_stream.get("height", 0)),
                "fps": eval(video_stream.get("r_frame_rate", "0/1")),
                "video_codec": video_stream.get("codec_name", ""),
                "audio_codec": audio_stream.get("codec_name", ""),
                "bitrate": int(format_info.get("bit_rate", 0)),
                "thumbnail_path": thumbnail_path
            }
            
        except Exception as e:
            logger.error(f"Error processing video {file_path}: {e}")
            return {"error": str(e)}
    
    async def _process_audio(self, file_path: str) -> Dict[str, Any]:
        """Process downloaded audio file"""
        try:
            # Use FFprobe to get audio info
            cmd = [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", "-show_streams", file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return {"error": "Failed to get audio info"}
            
            audio_info = json.loads(result.stdout)
            
            # Extract relevant info
            format_info = audio_info.get("format", {})
            audio_stream = next((s for s in audio_info.get("streams", []) if s.get("codec_type") == "audio"), {})
            
            return {
                "duration": float(format_info.get("duration", 0)),
                "sample_rate": int(audio_stream.get("sample_rate", 0)),
                "channels": int(audio_stream.get("channels", 0)),
                "audio_codec": audio_stream.get("codec_name", ""),
                "bitrate": int(format_info.get("bit_rate", 0))
            }
            
        except Exception as e:
            logger.error(f"Error processing audio {file_path}: {e}")
            return {"error": str(e)}
    
    async def download_media(self, media_items: List[Dict[str, Any]], session_id: str) -> List[Dict[str, Any]]:
        """
        Download multiple media items concurrently
        
        Args:
            media_items: List of media items with URLs and metadata
            session_id: Session ID for organization
        
        Returns:
            List of download results with file paths and metadata
        """
        if not media_items:
            return []
        
        # Check storage quota
        current_usage = self.session_storage_usage.get(session_id, 0)
        if current_usage >= self.max_storage_per_session:
            logger.warning(f"Storage quota exceeded for session {session_id}")
            return []
        
        logger.info(f"Starting download of {len(media_items)} media items for session {session_id}")
        
        # Create download tasks
        download_tasks = []
        for item in media_items:
            url = item.get("url", item.get("download_url", ""))
            if not url:
                continue
            
            # Generate filename from item info
            filename = None
            if "filename" in item:
                filename = item["filename"]
            elif "id" in item:
                extension = self._get_file_extension(url)
                filename = f"{item['id']}{extension}"
            
            task = self._download_file(url, session_id, filename)
            download_tasks.append((item, task))
        
        # Execute downloads with concurrency limit
        semaphore = asyncio.Semaphore(self.max_concurrent_downloads)
        
        async def download_with_semaphore(task):
            async with semaphore:
                return await task
        
        results = []
        for item, task in download_tasks:
            try:
                download_result = await download_with_semaphore(task)
                
                if download_result.get("success"):
                    # Process the downloaded file
                    file_path = download_result["file_path"]
                    media_type = download_result["media_type"]
                    
                    if media_type == "image":
                        process_result = await self._process_image(file_path)
                    elif media_type == "video":
                        process_result = await self._process_video(file_path)
                    elif media_type == "audio":
                        process_result = await self._process_audio(file_path)
                    else:
                        process_result = {}
                    
                    # Combine results
                    final_result = {
                        **item,
                        **download_result,
                        **process_result,
                        "session_id": session_id,
                        "download_time": time.time()
                    }
                    
                    results.append(final_result)
                else:
                    logger.error(f"Download failed for {item.get('url', 'unknown')}: {download_result.get('error')}")
                    
            except Exception as e:
                logger.error(f"Error in download task: {e}")
        
        logger.info(f"Download completed: {len(results)} successful, {len(media_items) - len(results)} failed")
        return results
    
    async def download_single_media(self, url: str, session_id: str, filename: str = None) -> Dict[str, Any]:
        """
        Download a single media item
        
        Args:
            url: Media URL
            session_id: Session ID for organization
            filename: Optional filename
        
        Returns:
            Download result with file path and metadata
        """
        media_items = [{"url": url, "filename": filename}]
        results = await self.download_media(media_items, session_id)
        return results[0] if results else {"error": "Download failed"}
    
    def get_session_storage_usage(self, session_id: str) -> Dict[str, Any]:
        """Get storage usage for a session"""
        usage = self.session_storage_usage.get(session_id, 0)
        return {
            "session_id": session_id,
            "used_bytes": usage,
            "used_mb": usage / (1024 * 1024),
            "limit_bytes": self.max_storage_per_session,
            "limit_mb": self.max_storage_per_session / (1024 * 1024),
            "percentage": (usage / self.max_storage_per_session) * 100
        }
    
    def cleanup_session_files(self, session_id: str) -> bool:
        """Clean up all files for a session"""
        try:
            session_dir = Path(f"sessions/{session_id}/downloads")
            if session_dir.exists():
                import shutil
                shutil.rmtree(session_dir)
            
            # Remove from storage tracking
            if session_id in self.session_storage_usage:
                del self.session_storage_usage[session_id]
            
            logger.info(f"Cleaned up files for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {e}")
            return False
    
    def get_download_statistics(self) -> Dict[str, Any]:
        """Get download service statistics"""
        return {
            "max_concurrent_downloads": self.max_concurrent_downloads,
            "download_timeout": self.download_timeout,
            "max_file_size": self.max_file_size,
            "retry_attempts": self.retry_attempts,
            "active_sessions": len(self.session_storage_usage),
            "total_storage_used": sum(self.session_storage_usage.values()),
            "max_storage_per_session": self.max_storage_per_session
        }

# Global instance
media_downloader_service = MediaDownloaderService() 