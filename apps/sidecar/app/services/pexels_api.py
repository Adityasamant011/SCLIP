"""
Pexels API Service for Sclip
Provides stock photo and video search capabilities
"""

import asyncio
import json
import os
from typing import Dict, List, Any, Optional
from urllib.parse import quote_plus
import aiohttp
import time

from ..utils.logger import get_logger

logger = get_logger(__name__)

class PexelsAPIService:
    """
    Pexels API service for stock media search
    Provides comprehensive image and video search with filtering and caching
    """
    
    def __init__(self):
        self.api_key = os.getenv("PEXELS_API_KEY")
        self.base_url = "https://api.pexels.com/v1"
        self.video_url = "https://api.pexels.com/videos"
        
        # Rate limiting
        self.requests_per_hour = 200  # Free tier limit
        self.requests_per_second = 5
        self.last_request_time = 0
        self.hourly_request_count = 0
        self.last_reset_hour = time.strftime("%Y-%m-%d-%H")
        
        # Cache for search results
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour
        
        # Orientation mappings
        self.orientation_mappings = {
            "landscape": "landscape",
            "portrait": "portrait", 
            "square": "square"
        }
        
        # Size mappings
        self.size_mappings = {
            "small": "small",
            "medium": "medium",
            "large": "large"
        }
        
        # Color mappings
        self.color_mappings = {
            "red": "red",
            "orange": "orange",
            "yellow": "yellow",
            "green": "green",
            "turquoise": "turquoise",
            "blue": "blue",
            "violet": "violet",
            "pink": "pink",
            "brown": "brown",
            "black": "black",
            "gray": "gray",
            "white": "white"
        }
        
        logger.info(f"Pexels API Service initialized with API key: {self.api_key[:8]}..." if self.api_key else "No API key")
    
    def _check_rate_limit(self) -> bool:
        """Check and enforce rate limits"""
        current_time = time.time()
        current_hour = time.strftime("%Y-%m-%d-%H")
        
        # Reset hourly counter if new hour
        if current_hour != self.last_reset_hour:
            self.hourly_request_count = 0
            self.last_reset_hour = current_hour
        
        # Check hourly limit
        if self.hourly_request_count >= self.requests_per_hour:
            logger.warning("Hourly API quota exceeded")
            return False
        
        # Check per-second limit
        if current_time - self.last_request_time < 1.0 / self.requests_per_second:
            time.sleep(1.0 / self.requests_per_second)
        
        return True
    
    def _build_search_params(self, query: str, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Build search parameters for Pexels API"""
        params = {
            "query": query,
            "per_page": min(filters.get("count", 15), 80),  # Max 80 per request
            "page": filters.get("page", 1)
        }
        
        if filters:
            # Add orientation filter
            if "orientation" in filters and filters["orientation"] in self.orientation_mappings:
                params["orientation"] = self.orientation_mappings[filters["orientation"]]
            
            # Add size filter
            if "size" in filters and filters["size"] in self.size_mappings:
                params["size"] = self.size_mappings[filters["size"]]
            
            # Add color filter
            if "color" in filters and filters["color"] in self.color_mappings:
                params["color"] = self.color_mappings[filters["color"]]
            
            # Add locale
            if "locale" in filters:
                params["locale"] = filters["locale"]
        
        return params
    
    def _parse_photo_results(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse photo search results"""
        results = []
        
        if "photos" not in response_data:
            logger.warning("No photos found in search response")
            return results
        
        for photo in response_data["photos"]:
            try:
                # Extract photo information
                photo_info = {
                    "id": photo.get("id", 0),
                    "url": photo.get("url", ""),
                    "photographer": photo.get("photographer", ""),
                    "photographer_url": photo.get("photographer_url", ""),
                    "width": photo.get("width", 0),
                    "height": photo.get("height", 0),
                    "alt": photo.get("alt", ""),
                    "src": {
                        "original": photo.get("src", {}).get("original", ""),
                        "large": photo.get("src", {}).get("large", ""),
                        "large2x": photo.get("src", {}).get("large2x", ""),
                        "medium": photo.get("src", {}).get("medium", ""),
                        "small": photo.get("src", {}).get("small", ""),
                        "portrait": photo.get("src", {}).get("portrait", ""),
                        "landscape": photo.get("src", {}).get("landscape", ""),
                        "tiny": photo.get("src", {}).get("tiny", "")
                    },
                    "avg_color": photo.get("avg_color", ""),
                    "liked": photo.get("liked", False),
                    "source": "pexels_photos"
                }
                
                # Validate required fields
                if photo_info["src"]["original"] and photo_info["width"] > 0:
                    results.append(photo_info)
                    
            except Exception as e:
                logger.error(f"Error parsing photo result: {e}")
                continue
        
        return results
    
    def _parse_video_results(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse video search results"""
        results = []
        
        if "videos" not in response_data:
            logger.warning("No videos found in search response")
            return results
        
        for video in response_data["videos"]:
            try:
                # Extract video information
                video_info = {
                    "id": video.get("id", 0),
                    "url": video.get("url", ""),
                    "user": {
                        "id": video.get("user", {}).get("id", 0),
                        "name": video.get("user", {}).get("name", ""),
                        "url": video.get("user", {}).get("url", "")
                    },
                    "width": video.get("width", 0),
                    "height": video.get("height", 0),
                    "duration": video.get("duration", 0),
                    "image": video.get("image", ""),
                    "video_files": video.get("video_files", []),
                    "video_pictures": video.get("video_pictures", []),
                    "avg_color": video.get("avg_color", ""),
                    "liked": video.get("liked", False),
                    "source": "pexels_videos"
                }
                
                # Validate required fields
                if video_info["image"] and video_info["width"] > 0:
                    results.append(video_info)
                    
            except Exception as e:
                logger.error(f"Error parsing video result: {e}")
                continue
        
        return results
    
    def _calculate_relevance_score(self, media_info: Dict[str, Any], topic: str) -> float:
        """Calculate relevance score for search result"""
        score = 0.0
        
        # Alt text relevance
        alt_text = media_info.get("alt", "").lower()
        topic_words = topic.lower().split()
        alt_matches = sum(1 for word in topic_words if word in alt_text)
        score += (alt_matches / len(topic_words)) * 0.4
        
        # Image quality (size)
        width = media_info.get("width", 0)
        height = media_info.get("height", 0)
        if width > 0 and height > 0:
            # Prefer larger images
            size_score = min((width * height) / (1920 * 1080), 1.0)
            score += size_score * 0.3
        
        # Color relevance (if specified)
        avg_color = media_info.get("avg_color", "")
        if avg_color:
            score += 0.1  # Bonus for having color information
        
        # Source reliability
        score += 0.2  # Pexels is a reliable stock media source
        
        return min(score, 1.0)
    
    async def search_photos(self, query: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Search for photos using Pexels API
        
        Args:
            query: Search query
            filters: Search filters (orientation, size, color, count, etc.)
        
        Returns:
            List of photo information dictionaries
        """
        if not self.api_key:
            logger.error("Pexels API key not configured")
            return []
        
        if not self._check_rate_limit():
            logger.error("Rate limit exceeded")
            return []
        
        # Check cache first
        cache_key = f"photos_{query}_{json.dumps(filters, sort_keys=True)}"
        if cache_key in self.cache:
            cache_time, cache_data = self.cache[cache_key]
            if time.time() - cache_time < self.cache_ttl:
                logger.info(f"Returning cached photo results for: {query}")
                return cache_data
        
        try:
            # Build search parameters
            params = self._build_search_params(query, filters)
            
            logger.info(f"Searching for photos: {query}")
            
            # Make API request
            headers = {"Authorization": self.api_key}
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/search", params=params, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status}")
                        return []
                    
                    response_data = await response.json()
            
            # Parse results
            results = self._parse_photo_results(response_data)
            
            # Calculate relevance scores
            for result in results:
                result["relevance_score"] = self._calculate_relevance_score(result, query)
            
            # Sort by relevance
            results.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            # Update rate limiting
            self.last_request_time = time.time()
            self.hourly_request_count += 1
            
            # Cache results
            self.cache[cache_key] = (time.time(), results)
            
            logger.info(f"Found {len(results)} photos for: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching photos: {e}")
            return []
    
    async def search_videos(self, query: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Search for videos using Pexels API
        
        Args:
            query: Search query
            filters: Search filters (orientation, size, count, etc.)
        
        Returns:
            List of video information dictionaries
        """
        if not self.api_key:
            logger.error("Pexels API key not configured")
            return []
        
        if not self._check_rate_limit():
            logger.error("Rate limit exceeded")
            return []
        
        # Check cache first
        cache_key = f"videos_{query}_{json.dumps(filters, sort_keys=True)}"
        if cache_key in self.cache:
            cache_time, cache_data = self.cache[cache_key]
            if time.time() - cache_time < self.cache_ttl:
                logger.info(f"Returning cached video results for: {query}")
                return cache_data
        
        try:
            # Build search parameters
            params = self._build_search_params(query, filters)
            
            logger.info(f"Searching for videos: {query}")
            
            # Make API request
            headers = {"Authorization": self.api_key}
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.video_url}/search", params=params, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status}")
                        return []
                    
                    response_data = await response.json()
            
            # Parse results
            results = self._parse_video_results(response_data)
            
            # Calculate relevance scores
            for result in results:
                result["relevance_score"] = self._calculate_relevance_score(result, query)
            
            # Sort by relevance
            results.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            # Update rate limiting
            self.last_request_time = time.time()
            self.hourly_request_count += 1
            
            # Cache results
            self.cache[cache_key] = (time.time(), results)
            
            logger.info(f"Found {len(results)} videos for: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching videos: {e}")
            return []
    
    async def search_media(self, query: str, media_type: str = "both", filters: Dict[str, Any] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search for both photos and videos
        
        Args:
            query: Search query
            media_type: Type of media to search ("photos", "videos", "both")
            filters: Search filters
        
        Returns:
            Dictionary with "photos" and/or "videos" lists
        """
        results = {}
        
        if media_type in ["photos", "both"]:
            results["photos"] = await self.search_photos(query, filters)
        
        if media_type in ["videos", "both"]:
            results["videos"] = await self.search_videos(query, filters)
        
        return results
    
    async def search_media_paginated(self, query: str, media_type: str = "both", 
                                   filters: Dict[str, Any] = None, max_results: int = 100) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search for media with pagination to get more results
        
        Args:
            query: Search query
            media_type: Type of media to search
            filters: Search filters
            max_results: Maximum number of results per type
        
        Returns:
            Dictionary with paginated results
        """
        results = {}
        
        if media_type in ["photos", "both"]:
            all_photos = []
            page = 1
            
            while len(all_photos) < max_results:
                page_filters = filters.copy() if filters else {}
                page_filters["page"] = page
                page_filters["count"] = min(80, max_results - len(all_photos))
                
                page_photos = await self.search_photos(query, page_filters)
                
                if not page_photos:
                    break
                
                all_photos.extend(page_photos)
                page += 1
                
                # Rate limiting between requests
                await asyncio.sleep(0.2)
            
            results["photos"] = all_photos[:max_results]
        
        if media_type in ["videos", "both"]:
            all_videos = []
            page = 1
            
            while len(all_videos) < max_results:
                page_filters = filters.copy() if filters else {}
                page_filters["page"] = page
                page_filters["count"] = min(80, max_results - len(all_videos))
                
                page_videos = await self.search_videos(query, page_filters)
                
                if not page_videos:
                    break
                
                all_videos.extend(page_videos)
                page += 1
                
                # Rate limiting between requests
                await asyncio.sleep(0.2)
            
            results["videos"] = all_videos[:max_results]
        
        return results
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """Get search service statistics"""
        return {
            "hourly_requests": self.hourly_request_count,
            "hourly_limit": self.requests_per_hour,
            "cache_size": len(self.cache),
            "last_reset": self.last_reset_hour
        }
    
    def clear_cache(self) -> None:
        """Clear the search result cache"""
        self.cache.clear()
        logger.info("Search cache cleared")

# Global instance
pexels_api_service = PexelsAPIService() 