"""
Simplified B-roll Finder Tool - Media search and download (without AI generation)
"""
import asyncio
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import json

from ..services.google_search import GoogleSearchService, SearchResult
from ..services.pexels_api import PexelsAPIService, PexelsMedia
from ..services.media_downloader import MediaDownloader, DownloadResult

logger = logging.getLogger(__name__)

@dataclass
class BrollSearchRequest:
    """Input schema for B-roll finder"""
    topic: str
    count: int = 10
    style: str = "cinematic"
    duration: str = "short"  # short, medium, long
    search_type: str = "both"  # images, videos, both
    sources: List[str] = None  # google, pexels, local
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

class BrollFinderSimple:
    """Simplified B-roll finder tool (without AI generation)"""
    
    def __init__(self, session_id: str = None):
        self.session_id = session_id or "default"
        
        # Initialize services
        self.google_search = GoogleSearchService()
        self.pexels_api = PexelsAPIService()
        self.media_downloader = MediaDownloader(f"downloads/{self.session_id}")
        
        # Default sources if none specified
        self.default_sources = ["local", "pexels", "google"]
        
        # Search statistics
        self.search_stats = {
            "total_found": 0,
            "total_downloaded": 0,
            "sources_used": [],
            "errors": []
        }
    
    async def find_broll(self, request: BrollSearchRequest) -> BrollSearchResult:
        """
        Main method to find and download B-roll content
        """
        logger.info(f"Starting B-roll search for topic: {request.topic}")
        
        # Set default sources if none specified
        if not request.sources:
            request.sources = self.default_sources.copy()
        
        # Initialize result containers
        all_clips = []
        all_file_paths = []
        all_metadata = []
        all_thumbnails = []
        all_source_types = []
        
        # Search from local resources first
        if "local" in request.sources:
            local_results = await self._search_local_resources(request)
            all_clips.extend(local_results["clips"])
            all_file_paths.extend(local_results["file_paths"])
            all_metadata.extend(local_results["metadata"])
            all_thumbnails.extend(local_results["thumbnails"])
            all_source_types.extend(local_results["source_types"])
        
        # Search from external sources
        external_results = await self._search_external_sources(request)
        all_clips.extend(external_results["clips"])
        all_file_paths.extend(external_results["file_paths"])
        all_metadata.extend(external_results["metadata"])
        all_thumbnails.extend(external_results["thumbnails"])
        all_source_types.extend(external_results["source_types"])
        
        # Create search summary
        search_summary = {
            "topic": request.topic,
            "total_found": len(all_clips),
            "sources_used": list(set(all_source_types)),
            "search_stats": self.search_stats,
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
    
    async def _search_local_resources(self, request: BrollSearchRequest) -> Dict:
        """Search local resources directory"""
        logger.info("Searching local resources...")
        
        clips = []
        file_paths = []
        metadata = []
        thumbnails = []
        source_types = []
        
        try:
            # Search in resources directory
            resources_dir = Path("resources")
            if not resources_dir.exists():
                logger.warning("Resources directory not found")
                return self._empty_search_result()
            
            # Search for images and videos
            search_patterns = []
            if request.search_type in ["images", "both"]:
                search_patterns.extend(["*.jpg", "*.jpeg", "*.png", "*.gif", "*.webp"])
            if request.search_type in ["videos", "both"]:
                search_patterns.extend(["*.mp4", "*.avi", "*.mov", "*.webm"])
            
            found_files = []
            for pattern in search_patterns:
                found_files.extend(resources_dir.rglob(pattern))
            
            # Filter by topic relevance (simple keyword matching)
            relevant_files = []
            topic_str = request.topic if isinstance(request.topic, str) else ""
            topic_keywords = topic_str.lower().split()
            
            for file_path in found_files:
                filename = file_path.name.lower()
                if any(keyword in filename for keyword in topic_keywords):
                    relevant_files.append(file_path)
            
            # Take top results
            relevant_files = relevant_files[:request.count]
            
            for file_path in relevant_files:
                clips.append(file_path.name)
                file_paths.append(str(file_path))
                
                # Create metadata
                file_metadata = {
                    "filename": file_path.name,
                    "file_size": file_path.stat().st_size,
                    "source": "local",
                    "relevance_score": 0.8,  # High relevance for local files
                    "file_type": file_path.suffix[1:].upper()
                }
                metadata.append(file_metadata)
                
                # Create thumbnail if it's an image
                if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    thumbnail_path = await self.media_downloader.create_thumbnail(str(file_path))
                    thumbnails.append(thumbnail_path or str(file_path))
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
    
    async def _search_external_sources(self, request: BrollSearchRequest) -> Dict:
        """Search external sources (Google, Pexels)"""
        logger.info("Searching external sources...")
        
        clips = []
        file_paths = []
        metadata = []
        thumbnails = []
        source_types = []
        
        # Search Google Custom Search
        if "google" in request.sources and request.search_type in ["images", "both"]:
            google_results = await self._search_google(request)
            clips.extend(google_results["clips"])
            file_paths.extend(google_results["file_paths"])
            metadata.extend(google_results["metadata"])
            thumbnails.extend(google_results["thumbnails"])
            source_types.extend(google_results["source_types"])
        
        # Search Pexels
        if "pexels" in request.sources:
            pexels_results = await self._search_pexels(request)
            clips.extend(pexels_results["clips"])
            file_paths.extend(pexels_results["file_paths"])
            metadata.extend(pexels_results["metadata"])
            thumbnails.extend(pexels_results["thumbnails"])
            source_types.extend(pexels_results["source_types"])
        
        return {
            "clips": clips,
            "file_paths": file_paths,
            "metadata": metadata,
            "thumbnails": thumbnails,
            "source_types": source_types
        }
    
    async def _search_google(self, request: BrollSearchRequest) -> Dict:
        """Search Google Custom Search"""
        logger.info("Searching Google Custom Search...")
        
        clips = []
        file_paths = []
        metadata = []
        thumbnails = []
        source_types = []
        
        try:
            # Search for images
            search_results = await self.google_search.search_images(
                query=request.topic,
                count=min(request.count, 10),
                size="large",
                image_type="photo",
                usage_rights="cc_publicdomain"
            )
            
            if search_results:
                # Download the images
                urls = [result.image_url for result in search_results]
                metadata_list = [
                    {
                        "title": result.title,
                        "snippet": result.snippet,
                        "source": "google",
                        "relevance_score": 0.7,
                        "usage_rights": result.usage_rights
                    }
                    for result in search_results
                ]
                
                download_results = await self.media_downloader.download_batch(urls, metadata_list)
                
                for i, download_result in enumerate(download_results):
                    if download_result.success:
                        clips.append(f"google_{i+1}")
                        file_paths.append(download_result.file_path)
                        metadata.append(download_result.metadata)
                        
                        # Create thumbnail
                        thumbnail_path = await self.media_downloader.create_thumbnail(download_result.file_path)
                        thumbnails.append(thumbnail_path or download_result.file_path)
                        
                        source_types.append("google")
                        
                        self.search_stats["total_downloaded"] += 1
            
            self.search_stats["sources_used"].append("google")
            
        except Exception as e:
            logger.error(f"Error searching Google: {e}")
            self.search_stats["errors"].append(f"Google search error: {e}")
        
        return {
            "clips": clips,
            "file_paths": file_paths,
            "metadata": metadata,
            "thumbnails": thumbnails,
            "source_types": source_types
        }
    
    async def _search_pexels(self, request: BrollSearchRequest) -> Dict:
        """Search Pexels API"""
        logger.info("Searching Pexels...")
        
        clips = []
        file_paths = []
        metadata = []
        thumbnails = []
        source_types = []
        
        try:
            # Search for photos
            if request.search_type in ["images", "both"]:
                pexels_photos = await self.pexels_api.search_photos(
                    query=request.topic,
                    count=min(request.count // 2, 15),
                    orientation="landscape",
                    size="large"
                )
                
                if pexels_photos:
                    # Download photos
                    urls = [photo.download_url for photo in pexels_photos]
                    metadata_list = [
                        {
                            "title": f"Pexels Photo {photo.id}",
                            "photographer": photo.photographer,
                            "source": "pexels",
                            "relevance_score": 0.8,
                            "license": "Free to use with attribution",
                            "pexels_id": photo.id
                        }
                        for photo in pexels_photos
                    ]
                    
                    download_results = await self.media_downloader.download_batch(urls, metadata_list)
                    
                    for i, download_result in enumerate(download_results):
                        if download_result.success:
                            clips.append(f"pexels_photo_{i+1}")
                            file_paths.append(download_result.file_path)
                            metadata.append(download_result.metadata)
                            
                            # Create thumbnail
                            thumbnail_path = await self.media_downloader.create_thumbnail(download_result.file_path)
                            thumbnails.append(thumbnail_path or download_result.file_path)
                            
                            source_types.append("pexels")
                            
                            self.search_stats["total_downloaded"] += 1
            
            # Search for videos
            if request.search_type in ["videos", "both"]:
                pexels_videos = await self.pexels_api.search_videos(
                    query=request.topic,
                    count=min(request.count // 2, 15),
                    orientation="landscape",
                    size="large"
                )
                
                if pexels_videos:
                    # Download videos
                    urls = [video.download_url for video in pexels_videos]
                    metadata_list = [
                        {
                            "title": f"Pexels Video {video.id}",
                            "photographer": video.photographer,
                            "source": "pexels",
                            "relevance_score": 0.8,
                            "license": "Free to use with attribution",
                            "pexels_id": video.id,
                            "duration": video.duration
                        }
                        for video in pexels_videos
                    ]
                    
                    download_results = await self.media_downloader.download_batch(urls, metadata_list)
                    
                    for i, download_result in enumerate(download_results):
                        if download_result.success:
                            clips.append(f"pexels_video_{i+1}")
                            file_paths.append(download_result.file_path)
                            metadata.append(download_result.metadata)
                            
                            # Use video thumbnail
                            thumbnails.append(download_result.file_path)
                            
                            source_types.append("pexels")
                            
                            self.search_stats["total_downloaded"] += 1
            
            self.search_stats["sources_used"].append("pexels")
            
        except Exception as e:
            logger.error(f"Error searching Pexels: {e}")
            self.search_stats["errors"].append(f"Pexels search error: {e}")
        
        return {
            "clips": clips,
            "file_paths": file_paths,
            "metadata": metadata,
            "thumbnails": thumbnails,
            "source_types": source_types
        }
    
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
            await self.media_downloader.cleanup_old_files(max_age_hours=1)
            logger.info(f"Cleaned up session files for {self.session_id}")
        except Exception as e:
            logger.error(f"Error cleaning up session files: {e}")
    
    def get_search_stats(self) -> Dict:
        """Get search statistics"""
        return self.search_stats.copy() 