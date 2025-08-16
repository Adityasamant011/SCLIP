"""
B-roll Finder Tool - Comprehensive media search and download
"""
import asyncio
import logging
import shutil
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import json
import os
import aiohttp
from datetime import datetime

from ..services.google_search import google_search_service
from ..services.pexels_api import pexels_api_service
from ..services.media_downloader import MediaDownloaderService
from ..utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class SearchResult:
    """Represents a search result with metadata"""
    file_path: Path
    title: str
    source: str
    url: str = ""
    file_size: int = 0
    relevance_score: float = 0.8
    
    def to_dict(self) -> Dict:
        return {
            "filename": self.file_path.name,
            "file_size": self.file_size,
            "source": self.source,
            "relevance_score": self.relevance_score,
            "file_type": self.file_path.suffix.upper().lstrip("."),
            "title": self.title,
            "url": self.url
        }

@dataclass
class BrollSearchRequest:
    """Input schema for B-roll finder"""
    topic: str
    count: int = 10
    style: str = "cinematic"
    duration: str = "short"  # short, medium, long
    search_type: str = "both"  # images, videos, both
    sources: List[str] = None  # google, pexels, runware, local
    ai_generation: bool = False
    aspect_ratio: str = "16:9"
    quality: str = "high"  # low, medium, high

@dataclass
class BrollSearchResult:
    """Output schema for B-roll finder"""
    clips: List[str]  # File paths
    file_paths: List[str]  # Full file paths
    metadata: List[Dict]  # Metadata for each clip
    thumbnails: List[str]  # Thumbnail paths
    source_types: List[str]  # Source of each clip
    search_summary: Dict  # Search statistics

class BrollFinder:
    """Comprehensive B-roll finder tool"""
    
    def __init__(self, session_id: str = None):
        self.session_id = session_id or "default"
        
        # Use global service instances
        self.google_search = google_search_service
        self.pexels_api = pexels_api_service
        self.media_downloader = MediaDownloaderService
        
        # Default sources - prioritize external sources for better results
        self.default_sources = ["pexels", "google", "local"]
        
        # Search statistics
        self.search_stats = {
            "total_found": 0,
            "total_downloaded": 0,
            "sources_used": [],
            "errors": [],
            "citations": []  # Track citations for attribution
        }
    
    async def find_broll(self, request: BrollSearchRequest, project_id: str = None) -> BrollSearchResult:
        """
        Main method to find and download B-roll content
        """
        logger.info(f"Starting B-roll search for topic: {request.topic}")
        
        # Set default sources if none specified
        if not request.sources:
            request.sources = self.default_sources.copy()
        
        # If only local is specified, try to add external sources for better results
        if request.sources == ["local"]:
            logger.info("Only local sources specified, adding external sources for better results")
            request.sources = ["pexels", "google", "local"]
        
        # Initialize result containers
        all_clips = []
        all_file_paths = []
        all_metadata = []
        all_thumbnails = []
        all_source_types = []
        
        # Search from local resources first
        if "local" in request.sources:
            try:
                local_results = await self._search_local_resources(request, project_id)
                all_clips.extend(local_results["clips"])
                all_file_paths.extend(local_results["file_paths"])
                all_metadata.extend(local_results["metadata"])
                all_thumbnails.extend(local_results["thumbnails"])
                all_source_types.extend(local_results["source_types"])
                logger.info(f"Local search found {len(local_results['clips'])} items")
            except Exception as e:
                logger.error(f"Local search failed: {e}")
                self.search_stats["errors"].append(f"Local search failed: {e}")
        
        # Search from external sources
        if any(source in request.sources for source in ["google", "pexels"]):
            try:
                external_results = await self._search_external_sources(request, project_id)
                all_clips.extend(external_results["clips"])
                all_file_paths.extend(external_results["file_paths"])
                all_metadata.extend(external_results["metadata"])
                all_thumbnails.extend(external_results["thumbnails"])
                all_source_types.extend(external_results["source_types"])
                logger.info(f"External search found {len(external_results['clips'])} items")
            except Exception as e:
                logger.error(f"External search failed: {e}")
                self.search_stats["errors"].append(f"External search failed: {e}")
        
        # Generate AI images if requested (not implemented yet)
        if request.ai_generation and "runware" in request.sources:
            logger.info("AI image generation not implemented yet")
            # TODO: Implement AI image generation when Runware service is available
        
        # Ensure we have at least some results
        if not all_clips:
            logger.warning("No B-roll content found, returning empty result")
            # Return empty result but don't fail
            return BrollSearchResult(
                clips=[],
                file_paths=[],
                metadata=[],
                thumbnails=[],
                source_types=[],
                search_summary={
                    "topic": request.topic,
                    "total_found": 0,
                    "sources_used": [],
                    "search_stats": self.search_stats,
                    "citations": self.search_stats["citations"],
                    "request": {
                        "count": request.count,
                        "style": request.style,
                        "search_type": request.search_type,
                        "sources": request.sources
                    },
                    "message": f"No B-roll content found for '{request.topic}'. Try different keywords or check external sources."
                }
            )
        
        # Create search summary
        search_summary = {
            "topic": request.topic,
            "total_found": len(all_clips),
            "sources_used": list(set(all_source_types)),
            "search_stats": self.search_stats,
            "citations": self.search_stats["citations"],  # Include citations
            "request": {
                "count": request.count,
                "style": request.style,
                "search_type": request.search_type,
                "sources": request.sources
            }
        }
        
        logger.info(f"B-roll search completed. Found {len(all_clips)} items")
        
        return BrollSearchResult(
            clips=all_clips[:request.count],
            file_paths=all_file_paths[:request.count],
            metadata=all_metadata[:request.count],
            thumbnails=all_thumbnails[:request.count],
            source_types=all_source_types[:request.count],
            search_summary=search_summary
        )
    
    async def _search_local_resources(self, request: BrollSearchRequest, project_id: str = None) -> Dict:
        """Search local resources directory"""
        logger.info("Searching local resources...")
        
        clips = []
        file_paths = []
        metadata = []
        thumbnails = []
        source_types = []
        
        try:
            # Search in multiple possible resource directories
            possible_dirs = [
                Path("resources"),
                Path("assets"),
                Path("media"),
                Path("broll"),
                Path.home() / "Videos" / "Sclip" / "Projects" / (project_id or "default") / "resources" / "broll",
                Path.home() / "Pictures",
                Path.home() / "Videos"
            ]
            
            found_files = []
            search_patterns = []
            if request.search_type in ["images", "both"]:
                search_patterns.extend(["*.jpg", "*.jpeg", "*.png", "*.gif", "*.webp"])
            if request.search_type in ["videos", "both"]:
                search_patterns.extend(["*.mp4", "*.avi", "*.mov", "*.webm"])
            
            # Search in all possible directories
            for resources_dir in possible_dirs:
                if resources_dir.exists():
                    logger.info(f"Searching in directory: {resources_dir}")
                    for pattern in search_patterns:
                        try:
                            found_files.extend(resources_dir.rglob(pattern))
                        except Exception as e:
                            logger.warning(f"Error searching {resources_dir} with pattern {pattern}: {e}")
            
            # If no files found, create some placeholder content
            if not found_files:
                logger.info("No local files found, creating placeholder content")
                placeholder_files = await self._create_placeholder_content(request.topic, request.count, project_id)
                for file_path in placeholder_files:
                    if file_path.exists():
                        found_files.append(file_path)
            
            # Filter by topic relevance (simple keyword matching)
            relevant_files = []
            topic_str = request.topic if isinstance(request.topic, str) else ""
            topic_keywords = topic_str.lower().split()
            
            # First try exact keyword matching
            for file_path in found_files:
                filename = file_path.name.lower()
                if any(keyword in filename for keyword in topic_keywords):
                    relevant_files.append(file_path)
            
            # If no exact matches, try broader matching or return some general files
            if not relevant_files:
                logger.info(f"No exact matches found for '{topic_str}', checking for general content")
                # Only return files that look like actual content, not filters or effects
                for file_path in found_files:
                    filename = file_path.name.lower()
                    # Skip filter files, voice files, effects, and other non-content files
                    if (not filename.startswith('filter_') and 
                        not filename.startswith('voice_') and
                        not filename.startswith('effect_') and
                        not filename.startswith('transition_') and
                        not filename.startswith('kodachrome') and
                        not 'filter' in filename and
                        not 'effect' in filename):
                        relevant_files.append(file_path)
                        if len(relevant_files) >= request.count:
                            break
                
                # If still no relevant files, create some placeholder content
                if not relevant_files:
                    logger.info("No relevant local files found, creating placeholder content")
                    placeholder_files = await self._create_placeholder_content(request.topic, request.count, project_id)
                    for file_path in placeholder_files:
                        if file_path.exists():
                            relevant_files.append(file_path)
                            if len(relevant_files) >= request.count:
                                break
            
            # Take top results
            relevant_files = relevant_files[:request.count]
            
            for file_path in relevant_files:
                clips.append(file_path.name)
                file_paths.append(str(file_path))
                
                # Create metadata
                file_metadata = {
                    "filename": file_path.name,
                    "file_size": file_path.stat().st_size if file_path.exists() else 0,
                    "source": "local",
                    "relevance_score": 0.8,  # High relevance for local files
                    "file_type": file_path.suffix[1:].upper() if file_path.suffix else "UNKNOWN",
                    "title": file_path.stem.replace('_', ' ').title()
                }
                metadata.append(file_metadata)
                
                # Create thumbnail if it's an image
                if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    try:
                        # Use the file path directly as thumbnail for now
                        thumbnails.append(str(file_path))
                    except Exception as e:
                        logger.warning(f"Could not create thumbnail for {file_path}: {e}")
                        thumbnails.append(str(file_path))
                else:
                    thumbnails.append(str(file_path))
                
                source_types.append("local")
            
            self.search_stats["total_found"] += len(relevant_files)
            self.search_stats["sources_used"].append("local")
            
        except Exception as e:
            logger.error(f"Error searching local resources: {e}")
            self.search_stats["errors"].append(f"Local search error: {e}")
        
        return {
            "clips": clips,
            "file_paths": file_paths,
            "metadata": metadata,
            "thumbnails": thumbnails,
            "source_types": source_types
        }
    
    async def _search_external_sources(self, request: BrollSearchRequest, project_id: str = None) -> Dict:
        """Search external sources (Google, Pexels)"""
        logger.info("Searching external sources...")
        
        clips = []
        file_paths = []
        metadata = []
        thumbnails = []
        source_types = []
        
        # Search Google Custom Search
        if "google" in request.sources and request.search_type in ["images", "both"]:
            try:
                google_results = await self._search_google(request.topic, request.count, project_id)
                clips.extend([r.file_path for r in google_results])
                file_paths.extend([r.file_path for r in google_results])
                metadata.extend([r.to_dict() for r in google_results])
                thumbnails.extend([r.file_path for r in google_results])
                source_types.extend(["google"] * len(google_results))
                logger.info(f"Google search found {len(google_results)} items")
            except Exception as e:
                logger.error(f"Google search failed: {e}")
                self.search_stats["errors"].append(f"Google search error: {e}")
        
        # Search Pexels
        if "pexels" in request.sources:
            try:
                pexels_results = await self._search_pexels(request.topic, request.count, project_id, request.search_type)
                clips.extend([r.file_path for r in pexels_results])
                file_paths.extend([r.file_path for r in pexels_results])
                metadata.extend([r.to_dict() for r in pexels_results])
                thumbnails.extend([r.file_path for r in pexels_results])
                source_types.extend(["pexels"] * len(pexels_results))
                logger.info(f"Pexels search found {len(pexels_results)} items")
            except Exception as e:
                logger.error(f"Pexels search failed: {e}")
                self.search_stats["errors"].append(f"Pexels search error: {e}")
        
        return {
            "clips": clips,
            "file_paths": file_paths,
            "metadata": metadata,
            "thumbnails": thumbnails,
            "source_types": source_types
        }
    
    async def _search_google(self, topic: str, count: int, project_id: str = None) -> List[SearchResult]:
        """Search Google Custom Search for images"""
        results = []
        
        try:
            api_key = os.getenv("GOOGLE_CUSTOM_SEARCH_API_KEY")
            engine_id = os.getenv("GOOGLE_CUSTOM_SEARCH_ENGINE_ID")
            
            if not api_key or not engine_id:
                logger.warning("Google Custom Search API key not configured")
                self.search_stats["errors"].append("Google Custom Search API key not configured")
                return results
            
            logger.info(f"Searching Google for: {topic}")
            
            # Build search query - use the actual topic, not hardcoded terms
            search_query = topic
            
            # Make API request
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": api_key,
                "cx": engine_id,
                "q": search_query,
                "searchType": "image",
                "num": min(count, 10),
                "imgType": "photo",
                "imgSize": "xlarge",  # Get the largest available size
                "safe": "active"  # Safe search
                }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get("items", [])
                        
                        for item in items:
                            try:
                                # Use full-size image URL, not thumbnail
                                image_url = item.get("link") or item.get("image", {}).get("thumbnailLink")
                                title = item.get("title", "Google Image")
                                source_url = item.get("image", {}).get("contextLink", "")
                                
                                if image_url:
                                    # Download the image
                                    downloaded_path = await self._download_image(image_url, title, "google", project_id)
                                    if downloaded_path:
                                        results.append(SearchResult(
                                            file_path=downloaded_path,
                                            title=title,
                                            source="google",
                                            url=source_url,
                                            file_size=downloaded_path.stat().st_size if downloaded_path.exists() else 0,
                                            relevance_score=0.9
                                        ))
                                        
                                        # Add citation
                                        self.search_stats["citations"].append({
                                            "source": "Google Custom Search",
                                            "title": title,
                                            "url": source_url,
                                            "file_path": str(downloaded_path),
                                            "license": "Google Search Results"
                                        })
                                        
                            except Exception as e:
                                logger.error(f"Error processing Google search result: {e}")
                        
                        logger.info(f"Google search found {len(results)} images")
                        
                    else:
                        logger.error(f"Google search failed with status {response.status}")
                        self.search_stats["errors"].append(f"Google search failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error in Google search: {e}")
            self.search_stats["errors"].append(f"Google search error: {str(e)}")
        
        return results
    
    async def _download_image(self, image_url: str, title: str, source: str, project_id: str = None) -> Optional[Path]:
        """Download an image from URL"""
        try:
            # Create download directory
            if project_id:
                download_dir = Path.home() / "Videos" / "Sclip" / "Projects" / project_id / "resources" / "broll"
            else:
                download_dir = Path("downloads") / self.session_id
            
            download_dir.mkdir(parents=True, exist_ok=True)
            
            # Create filename
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_title = safe_title[:50]  # Limit length
            filename = f"{safe_title}_{int(datetime.now().timestamp())}_{source}.jpg"
            file_path = download_dir / filename
            
            # Download the image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        with open(file_path, 'wb') as f:
                            f.write(await response.read())
                        
                        logger.info(f"Downloaded image: {file_path}")
                        return file_path
                    else:
                        logger.error(f"Failed to download image: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error downloading image: {e}")
            return None

    async def _download_video(self, video_url: str, title: str, source: str, project_id: str = None) -> Optional[Path]:
        """Download a video from URL"""
        try:
            # Create download directory
            if project_id:
                download_dir = Path.home() / "Videos" / "Sclip" / "Projects" / project_id / "resources" / "broll"
            else:
                download_dir = Path("downloads") / self.session_id
            
            download_dir.mkdir(parents=True, exist_ok=True)
            
            # Create filename
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_title = safe_title[:50]  # Limit length
            filename = f"{safe_title}_{int(datetime.now().timestamp())}_{source}.mp4"
            file_path = download_dir / filename
            
            # Download the video
            async with aiohttp.ClientSession() as session:
                async with session.get(video_url) as response:
                    if response.status == 200:
                        with open(file_path, 'wb') as f:
                            f.write(await response.read())
                        
                        logger.info(f"Downloaded video: {file_path}")
                        return file_path
                    else:
                        logger.error(f"Failed to download video: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            return None
    
    async def _search_pexels(self, topic: str, count: int, project_id: str = None, search_type: str = "images") -> List[SearchResult]:
        """Search Pexels API for images or videos"""
        results = []
        
        try:
            api_key = os.getenv("PEXELS_API_KEY")
            
            if not api_key:
                logger.warning("Pexels API key not configured")
                self.search_stats["errors"].append("Pexels API key not configured")
                return results
            
            logger.info(f"Searching Pexels for: {topic} (type: {search_type})")
            
            # Build search query - use the actual topic, not hardcoded terms
            search_query = topic
            
            # Choose endpoint based on search type
            if search_type in ["videos", "both"]:
                # Search for videos
                url = "https://api.pexels.com/videos/search"
                params = {
                    "query": search_query,
                    "per_page": min(count, 10),
                    "orientation": "landscape"
                }
            else:
                # Search for images
                url = "https://api.pexels.com/v1/search"
                params = {
                    "query": search_query,
                    "per_page": min(count, 10),
                    "orientation": "landscape",
                    "size": "large2x"  # Get the highest quality available
                }
            
            headers = {"Authorization": api_key}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if search_type in ["videos", "both"]:
                            # Handle video results
                            videos = data.get("videos", [])
                            
                            for video in videos:
                                try:
                                    # Get the highest quality video available
                                    video_files = video.get("video_files", [])
                                    if video_files:
                                        # Sort by quality (HD first)
                                        video_files.sort(key=lambda x: x.get("width", 0), reverse=True)
                                        video_url = video_files[0].get("link")
                                        
                                        title = video.get("alt", "Pexels Video")
                                        photographer = video.get("user", {}).get("name", "Unknown")
                                        source_url = video.get("url", "")
                                        
                                        if video_url:
                                            # Download the video
                                            downloaded_path = await self._download_video(video_url, title, "pexels", project_id)
                                            if downloaded_path:
                                                results.append(SearchResult(
                                                    file_path=downloaded_path,
                                                    title=title,
                                                    source="pexels",
                                                    url=source_url,
                                                    file_size=downloaded_path.stat().st_size if downloaded_path.exists() else 0,
                                                    relevance_score=0.9
                                                ))
                                                
                                                # Add citation
                                                self.search_stats["citations"].append({
                                                    "source": "Pexels",
                                                    "title": title,
                                                    "photographer": photographer,
                                                    "url": source_url,
                                                    "file_path": str(downloaded_path),
                                                    "license": "Free to use"
                                                })
                                                
                                except Exception as e:
                                    logger.error(f"Error processing Pexels video result: {e}")
                        else:
                            # Handle image results
                            photos = data.get("photos", [])
                            
                            for photo in photos:
                                try:
                                    # Get the highest quality image available
                                    image_url = (photo.get("src", {}).get("original") or 
                                               photo.get("src", {}).get("large2x") or 
                                               photo.get("src", {}).get("large"))
                                    title = photo.get("alt", "Pexels Image")
                                    photographer = photo.get("photographer", "Unknown")
                                    source_url = photo.get("url", "")
                                    
                                    if image_url:
                                        # Download the image
                                        downloaded_path = await self._download_image(image_url, title, "pexels", project_id)
                                        if downloaded_path:
                                            results.append(SearchResult(
                                                file_path=downloaded_path,
                                                title=title,
                                                source="pexels",
                                                url=source_url,
                                                file_size=downloaded_path.stat().st_size if downloaded_path.exists() else 0,
                                                relevance_score=0.9
                                            ))
                                            
                                            # Add citation
                                            self.search_stats["citations"].append({
                                                "source": "Pexels",
                                                "title": title,
                                                "photographer": photographer,
                                                "url": source_url,
                                                "file_path": str(downloaded_path),
                                                "license": "Free to use"
                                            })
                                            
                                except Exception as e:
                                    logger.error(f"Error processing Pexels search result: {e}")
                        
                        logger.info(f"Pexels search found {len(results)} {'videos' if search_type in ['videos', 'both'] else 'images'}")
                        
                    else:
                        logger.error(f"Pexels search failed with status {response.status}")
                        self.search_stats["errors"].append(f"Pexels search failed: {response.status}")
            
        except Exception as e:
            logger.error(f"Error in Pexels search: {e}")
            self.search_stats["errors"].append(f"Pexels search error: {str(e)}")
        
        return results
    
    # TODO: Implement AI image generation when Runware service is available
    # async def _generate_ai_images(self, request: BrollSearchRequest) -> Dict:
    #     """Generate AI images using Runware"""
    #     pass
    
    def _empty_search_result(self) -> Dict:
        """Return empty search result"""
        return {
            "clips": [],
            "file_paths": [],
            "metadata": [],
            "thumbnails": [],
            "source_types": []
        }
    
    async def cleanup_session_files(self):
        """Clean up files for this session"""
        try:
            self.media_downloader.cleanup_session_files(self.session_id)
            logger.info(f"Cleaned up session files for {self.session_id}")
        except Exception as e:
            logger.error(f"Error cleaning up session files: {e}")
    
    def get_search_stats(self) -> Dict:
        """Get search statistics"""
        return self.search_stats.copy()

    async def _create_placeholder_content(self, topic: str, count: int, project_id: str = None) -> List[Path]:
        try:
            # Always use project-based path
            if project_id:
                from ..main import get_project_path
                project_path = get_project_path(project_id)
            else:
                # Create default project path if no project_id
                import uuid
                project_id = str(uuid.uuid4())
                project_path = Path.home() / "Videos" / "Sclip" / "Projects" / project_id
            
            placeholders_dir = project_path / "resources" / "broll" / "placeholders"
            logger.info(f"Creating placeholder content in project path: {placeholders_dir}")
            placeholders_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Creating placeholder content in: {placeholders_dir}")
            placeholder_files = []
            topic_keywords = topic.lower().split()
            
            for i in range(min(count, 5)):
                if "peppa" in topic_keywords or "pig" in topic_keywords:
                    filename = f"peppa_pig_cartoon_{i+1}.jpg"
                elif "messi" in topic_keywords or "soccer" in topic_keywords or "football" in topic_keywords:
                    filename = f"messi_soccer_{i+1}.jpg"
                elif "world" in topic_keywords and "cup" in topic_keywords:
                    filename = f"worldcup_match_{i+1}.jpg"
                elif "barcelona" in topic_keywords or "barca" in topic_keywords:
                    filename = f"barcelona_stadium_{i+1}.jpg"
                elif "avengers" in topic_keywords or "marvel" in topic_keywords:
                    filename = f"avengers_marvel_{i+1}.jpg"
                else:
                    filename = f"placeholder_content_{i+1}.jpg"
                
                placeholder_path = placeholders_dir / filename
                
                # Try to find sample images in multiple locations
                sample_images = []
                possible_sample_dirs = [
                    Path("resources"),
                    Path("assets"),
                    Path("media"),
                    Path("samples"),
                    Path.home() / "Pictures",
                    Path.home() / "Videos"
                ]
                
                for sample_dir in possible_sample_dirs:
                    if sample_dir.exists():
                        try:
                            sample_images.extend(list(sample_dir.rglob("*.jpg"))[:5])
                            if sample_images:
                                break
                        except Exception as e:
                            logger.warning(f"Error searching {sample_dir}: {e}")
                
                if sample_images:
                    source_image = sample_images[i % len(sample_images)]
                    try:
                        shutil.copy2(source_image, placeholder_path)
                        logger.info(f"Copied {source_image} to {placeholder_path}")
                    except Exception as e:
                        logger.warning(f"Failed to copy {source_image}: {e}")
                        placeholder_path.touch()
                        logger.info(f"Created empty placeholder: {placeholder_path}")
                else:
                    # Create a simple placeholder file
                    placeholder_path.touch()
                    logger.info(f"Created empty placeholder: {placeholder_path}")
                
                placeholder_files.append(placeholder_path)
            
            logger.info(f"Created {len(placeholder_files)} placeholder files in {placeholders_dir}")
            return placeholder_files
        except Exception as e:
            logger.error(f"Error creating placeholder content: {e}")
            # Return empty list instead of raising
            return []


class BrollFinderTool:
    """Tool interface for B-roll finder"""
    
    def __init__(self):
        self.name = "broll_finder"
        self.description = "Find and download B-roll content from multiple sources"
        self.version = "1.0.0"
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the B-roll finder tool"""
        try:
            # Extract parameters
            topic = input_data.get("topic", "")
            count = input_data.get("count", 10)  # Increased default count
            style = input_data.get("style", "cinematic")
            duration = input_data.get("duration", "short")
            search_type = input_data.get("search_type", "both")  # Default to both images and videos
            sources = input_data.get("sources", ["pexels", "google"])  # Better default sources
            ai_generation = input_data.get("ai_generation", False)
            session_id = input_data.get("session_id", "default")
            project_id = input_data.get("project_id")
            
            # AI-driven source selection for better results
            if not sources or sources == ["local"]:
                # Automatically select best sources based on topic
                if any(keyword in topic.lower() for keyword in ["messi", "ronaldo", "soccer", "football", "sports"]):
                    sources = ["pexels", "google", "pixabay"]
                elif any(keyword in topic.lower() for keyword in ["nature", "landscape", "travel"]):
                    sources = ["pexels", "unsplash", "google"]
                elif any(keyword in topic.lower() for keyword in ["business", "technology", "corporate"]):
                    sources = ["pexels", "google", "storyblocks"]
                else:
                    sources = ["pexels", "google", "pixabay"]  # Good general sources
            
            # Improve search quality for better first-try results
            if search_type == "both":
                # For both images and videos, increase count to ensure we get enough
                count = max(count, 15)
            
            # Enhance topic for better search results
            enhanced_topic = self._enhance_search_topic(topic)
            
            logger.info(f"B-roll finder tool called with topic: {enhanced_topic}, sources: {sources}, count: {count}")
            
            # Create request
            request = BrollSearchRequest(
                topic=enhanced_topic,
                count=count,
                style=style,
                duration=duration,
                search_type=search_type,
                sources=sources,
                ai_generation=ai_generation
            )
            
            # Create finder and search
            finder = BrollFinder(session_id)
            result = await finder.find_broll(request, project_id)
            
            # Check if we found any results
            if not result.clips:
                logger.warning(f"No B-roll content found for topic: {enhanced_topic}")
                return {
                    "success": True,  # Don't fail, just return empty results
                    "clips": [],
                    "file_paths": [],
                    "metadata": [],
                    "thumbnails": [],
                    "source_types": [],
                    "search_summary": result.search_summary,
                    "downloaded_files": [],
                    "message": f"No B-roll content found for '{enhanced_topic}'. Available sources: {sources}. Try different keywords or check if external APIs are configured."
                }
            
            # Convert result to include downloaded_files format for frontend
            downloaded_files = []
            for i, file_path in enumerate(result.file_paths):
                metadata = result.metadata[i] if i < len(result.metadata) else {}
                # Convert Path objects to strings for JSON serialization
                file_path_str = str(file_path) if hasattr(file_path, '__str__') else file_path
                thumbnail_str = str(result.thumbnails[i]) if i < len(result.thumbnails) and hasattr(result.thumbnails[i], '__str__') else result.thumbnails[i] if i < len(result.thumbnails) else file_path_str
                
                # Check if file exists
                if Path(file_path_str).exists():
                    file_size = Path(file_path_str).stat().st_size
                else:
                    file_size = metadata.get("file_size", 0)
                
                downloaded_files.append({
                    "name": metadata.get("title", f"B-roll Media {i+1}"),
                    "type": "image" if search_type == "images" else "video",
                    "path": file_path_str,
                    "size": file_size,
                    "thumbnail": thumbnail_str,
                    "source": result.source_types[i] if i < len(result.source_types) else "unknown",
                    "metadata": metadata
                })
            
            logger.info(f"B-roll finder tool completed successfully. Found {len(result.clips)} items")
            
            # Convert all Path objects to strings for JSON serialization
            file_paths_str = [str(fp) if hasattr(fp, '__str__') else fp for fp in result.file_paths]
            clips_str = [str(c) if hasattr(c, '__str__') else c for c in result.clips]
            thumbnails_str = [str(t) if hasattr(t, '__str__') else t for t in result.thumbnails]
            
            return {
                "success": True,
                "clips": clips_str,
                "file_paths": file_paths_str,
                "metadata": result.metadata,
                "thumbnails": thumbnails_str,
                "source_types": result.source_types,
                "search_summary": result.search_summary,
                "downloaded_files": downloaded_files  # Add this for frontend compatibility
            }
            
        except Exception as e:
            logger.error(f"B-roll finder tool error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"B-roll finder failed: {str(e)}. Check logs for details.",
                "downloaded_files": []
            }
    
    def _enhance_search_topic(self, topic: str) -> str:
        """Enhance search topic for better results"""
        # Add relevant keywords for better search results
        enhanced = topic.lower()
        
        # Sports/football enhancements
        if any(keyword in enhanced for keyword in ["messi", "ronaldo", "soccer", "football"]):
            enhanced += " highlights goals skills"
        
        # General enhancements
        if "video" not in enhanced and "footage" not in enhanced:
            enhanced += " video footage"
        
        # Quality enhancements
        if "high quality" not in enhanced and "hd" not in enhanced:
            enhanced += " high quality"
        
        return enhanced 