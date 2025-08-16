"""
Google Custom Search Service for Sclip
Provides image search capabilities for B-roll finder
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

class GoogleCustomSearchService:
    """
    Google Custom Search API service for image search
    Provides comprehensive image search with filtering and caching
    """
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_CUSTOM_SEARCH_API_KEY")
        self.search_engine_id = os.getenv("GOOGLE_CUSTOM_SEARCH_ENGINE_ID")
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        
        # Rate limiting
        self.requests_per_day = 10000  # Free tier limit
        self.requests_per_second = 10
        self.last_request_time = 0
        self.daily_request_count = 0
        self.last_reset_date = time.strftime("%Y-%m-%d")
        
        # Cache for search results
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour
        
        # Image size mappings
        self.size_mappings = {
            "small": "small",
            "medium": "medium", 
            "large": "large",
            "xlarge": "xlarge"
        }
        
        # Image type mappings
        self.type_mappings = {
            "face": "face",
            "photo": "photo",
            "clipart": "clipart",
            "lineart": "lineart"
        }
        
        # Usage rights mappings
        self.rights_mappings = {
            "free_to_use": "cc_publicdomain|cc_attribute|cc_sharealike|cc_noncommercial|cc_nonderived",
            "free_to_modify": "cc_publicdomain|cc_attribute|cc_sharealike|cc_nonderived"
        }
        
        logger.info(f"Google Custom Search Service initialized with engine ID: {self.search_engine_id}")
    
    def _check_rate_limit(self) -> bool:
        """Check and enforce rate limits"""
        current_time = time.time()
        current_date = time.strftime("%Y-%m-%d")
        
        # Reset daily counter if new day
        if current_date != self.last_reset_date:
            self.daily_request_count = 0
            self.last_reset_date = current_date
        
        # Check daily limit
        if self.daily_request_count >= self.requests_per_day:
            logger.warning("Daily API quota exceeded")
            return False
        
        # Check per-second limit
        if current_time - self.last_request_time < 1.0 / self.requests_per_second:
            time.sleep(1.0 / self.requests_per_second)
        
        return True
    
    def _build_search_query(self, topic: str, filters: Dict[str, Any] = None) -> str:
        """Build optimized search query with filters"""
        query = topic.strip()
        
        if filters:
            # Add size filter
            if "size" in filters and filters["size"] in self.size_mappings:
                query += f" size:{self.size_mappings[filters['size']]}"
            
            # Add type filter
            if "type" in filters and filters["type"] in self.type_mappings:
                query += f" type:{self.type_mappings[filters['type']]}"
            
            # Add usage rights filter
            if "rights" in filters and filters["rights"] in self.rights_mappings:
                query += f" rights:{self.rights_mappings[filters['rights']]}"
            
            # Add safe search
            if filters.get("safe_search", True):
                query += " safe:active"
        
        return query
    
    def _build_search_url(self, query: str, filters: Dict[str, Any] = None) -> str:
        """Build complete search URL with parameters"""
        params = {
            "key": self.api_key,
            "cx": self.search_engine_id,
            "q": query,
            "searchType": "image",
            "num": min(filters.get("count", 10), 10),  # Max 10 per request
            "start": filters.get("start", 1)
        }
        
        # Add additional filters
        if filters:
            if "size" in filters and filters["size"] in self.size_mappings:
                params["imgSize"] = self.size_mappings[filters["size"]]
            
            if "type" in filters and filters["type"] in self.type_mappings:
                params["imgType"] = self.type_mappings[filters["type"]]
            
            if "rights" in filters and filters["rights"] in self.rights_mappings:
                params["rights"] = self.rights_mappings[filters["rights"]]
            
            if filters.get("safe_search", True):
                params["safe"] = "active"
        
        # Build URL
        param_strings = [f"{k}={quote_plus(str(v))}" for k, v in params.items()]
        return f"{self.base_url}?{'&'.join(param_strings)}"
    
    def _parse_search_results(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse and validate search results"""
        results = []
        
        if "items" not in response_data:
            logger.warning("No items found in search response")
            return results
        
        for item in response_data["items"]:
            try:
                # Extract image information
                image_info = {
                    "url": item.get("link", ""),
                    "thumbnail": item.get("image", {}).get("thumbnailLink", ""),
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "context": item.get("image", {}).get("contextLink", ""),
                    "width": item.get("image", {}).get("width", 0),
                    "height": item.get("image", {}).get("height", 0),
                    "size": item.get("image", {}).get("byteSize", 0),
                    "mime_type": item.get("mime", ""),
                    "source": "google_custom_search"
                }
                
                # Validate required fields
                if image_info["url"] and image_info["thumbnail"]:
                    results.append(image_info)
                    
            except Exception as e:
                logger.error(f"Error parsing search result: {e}")
                continue
        
        return results
    
    def _calculate_relevance_score(self, image_info: Dict[str, Any], topic: str) -> float:
        """Calculate relevance score for search result"""
        score = 0.0
        
        # Title relevance
        title = image_info.get("title", "")
        title = title.lower() if isinstance(title, str) else ""
        topic_str = topic if isinstance(topic, str) else ""
        topic_words = topic_str.lower().split()
        title_matches = sum(1 for word in topic_words if word in title)
        score += (title_matches / len(topic_words)) * 0.4
        
        # Snippet relevance
        snippet = image_info.get("snippet", "")
        snippet = snippet.lower() if isinstance(snippet, str) else ""
        snippet_matches = sum(1 for word in topic_words if word in snippet)
        score += (snippet_matches / len(topic_words)) * 0.3
        
        # Image quality (size)
        width = image_info.get("width", 0)
        height = image_info.get("height", 0)
        if width > 0 and height > 0:
            # Prefer larger images
            size_score = min((width * height) / (1920 * 1080), 1.0)
            score += size_score * 0.2
        
        # Source reliability
        score += 0.1  # Google Custom Search is generally reliable
        
        return min(score, 1.0)
    
    async def search_images(self, topic: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Search for images using Google Custom Search API
        
        Args:
            topic: Search topic/query
            filters: Search filters (size, type, rights, count, etc.)
        
        Returns:
            List of image information dictionaries
        """
        if not self.api_key or not self.search_engine_id:
            logger.error("Google Custom Search API credentials not configured")
            return []
        
        if not self._check_rate_limit():
            logger.error("Rate limit exceeded")
            return []
        
        # Check cache first
        cache_key = f"{topic}_{json.dumps(filters, sort_keys=True)}"
        if cache_key in self.cache:
            cache_time, cache_data = self.cache[cache_key]
            if time.time() - cache_time < self.cache_ttl:
                logger.info(f"Returning cached results for: {topic}")
                return cache_data
        
        try:
            # Build search query and URL
            query = self._build_search_query(topic, filters)
            search_url = self._build_search_url(query, filters)
            
            logger.info(f"Searching for images: {topic}")
            
            # Make API request
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url) as response:
                    if response.status != 200:
                        logger.error(f"API request failed: {response.status}")
                        return []
                    
                    response_data = await response.json()
                    
                    # Check for API errors
                    if "error" in response_data:
                        logger.error(f"API error: {response_data['error']}")
                        return []
            
            # Parse results
            results = self._parse_search_results(response_data)
            
            # Calculate relevance scores
            for result in results:
                result["relevance_score"] = self._calculate_relevance_score(result, topic)
            
            # Sort by relevance
            results.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            # Update rate limiting
            self.last_request_time = time.time()
            self.daily_request_count += 1
            
            # Cache results
            self.cache[cache_key] = (time.time(), results)
            
            logger.info(f"Found {len(results)} images for: {topic}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching images: {e}")
            return []
    
    async def search_images_paginated(self, topic: str, filters: Dict[str, Any] = None, 
                                    max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Search for images with pagination to get more results
        
        Args:
            topic: Search topic/query
            filters: Search filters
            max_results: Maximum number of results to return
        
        Returns:
            List of image information dictionaries
        """
        all_results = []
        start_index = 1
        
        while len(all_results) < max_results:
            # Update filters for pagination
            page_filters = filters.copy() if filters else {}
            page_filters["start"] = start_index
            page_filters["count"] = min(10, max_results - len(all_results))
            
            # Search for this page
            page_results = await self.search_images(topic, page_filters)
            
            if not page_results:
                break
            
            all_results.extend(page_results)
            start_index += len(page_results)
            
            # Rate limiting between requests
            await asyncio.sleep(0.1)
        
        return all_results[:max_results]
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """Get search service statistics"""
        return {
            "daily_requests": self.daily_request_count,
            "daily_limit": self.requests_per_day,
            "cache_size": len(self.cache),
            "last_reset": self.last_reset_date
        }
    
    def clear_cache(self) -> None:
        """Clear the search result cache"""
        self.cache.clear()
        logger.info("Search cache cleared")

# Global instance
google_search_service = GoogleCustomSearchService() 