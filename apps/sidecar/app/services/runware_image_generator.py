"""
Runware AI Image Generation Service
"""
import os
import json
import asyncio
import aiohttp
import websockets
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class GenerationRequest:
    """Represents an image generation request"""
    prompt: str
    width: int = 1024
    height: int = 1024
    model: str = "runware:100@1"
    steps: int = 25
    cfg_scale: float = 4.0
    negative_prompt: str = ""
    number_results: int = 1

@dataclass
class GenerationResult:
    """Represents a generation result"""
    task_uuid: str
    image_url: str
    prompt: str
    model: str
    width: int
    height: int
    generation_time: float
    cost: float

class RunwareImageGenerator:
    """Service for Runware AI image generation"""
    
    def __init__(self):
        self.api_key = os.getenv("RUNWARE_API_KEY")
        self.ws_url = "wss://api.runware.ai/ws"
        self.rest_url = "https://api.runware.ai/v1"
        
        if not self.api_key:
            logger.warning("Runware API key not configured")
        
        # Popular models for different styles
        self.style_models = {
            "cinematic": "runware:100@1",
            "documentary": "runware:97@2", 
            "social_media": "runware:100@1",
            "artistic": "runware:97@2",
            "realistic": "runware:100@1",
            "cartoon": "runware:97@2"
        }
        
        # Aspect ratio presets
        self.aspect_ratios = {
            "16:9": (1920, 1080),
            "9:16": (1080, 1920),
            "1:1": (1024, 1024),
            "4:3": (1366, 1024),
            "3:2": (1536, 1024)
        }
    
    def _build_generation_request(self, request: GenerationRequest) -> Dict:
        """Build the generation request payload"""
        return {
            "taskType": "imageInference",
            "taskUUID": f"task_{asyncio.get_event_loop().time()}",
            "positivePrompt": request.prompt,
            "width": request.width,
            "height": request.height,
            "model": request.model,
            "steps": request.steps,
            "CFGScale": request.cfg_scale,
            "numberResults": request.number_results
        }
    
    async def generate_image_websocket(
        self, 
        request: GenerationRequest,
        progress_callback: Optional[Callable] = None
    ) -> Optional[GenerationResult]:
        """
        Generate image using WebSocket for real-time updates
        """
        if not self.api_key:
            logger.error("Runware API key not configured")
            return None
        
        try:
            payload = self._build_generation_request(request)
            
            async with websockets.connect(
                self.ws_url,
                extra_headers={"Authorization": f"Bearer {self.api_key}"}
            ) as websocket:
                # Send generation request
                await websocket.send(json.dumps(payload))
                
                start_time = asyncio.get_event_loop().time()
                
                while True:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)
                        
                        if progress_callback:
                            progress_callback(data)
                        
                        # Check if generation is complete
                        if data.get("status") == "completed":
                            generation_time = asyncio.get_event_loop().time() - start_time
                            
                            return GenerationResult(
                                task_uuid=data.get("taskUUID", ""),
                                image_url=data.get("imageUrl", ""),
                                prompt=request.prompt,
                                model=request.model,
                                width=request.width,
                                height=request.height,
                                generation_time=generation_time,
                                cost=0.0006  # Runware's base cost
                            )
                        
                        # Check for errors
                        if data.get("status") == "error":
                            logger.error(f"Generation error: {data.get('error', 'Unknown error')}")
                            return None
                            
                    except websockets.exceptions.ConnectionClosed:
                        logger.error("WebSocket connection closed")
                        return None
                        
        except Exception as e:
            logger.error(f"Error in WebSocket generation: {e}")
            return None
    
    async def generate_image_rest(self, request: GenerationRequest) -> Optional[GenerationResult]:
        """
        Generate image using REST API (fallback)
        """
        if not self.api_key:
            logger.error("Runware API key not configured")
            return None
        
        try:
            payload = self._build_generation_request(request)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.rest_url}/generate",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        return GenerationResult(
                            task_uuid=data.get("taskUUID", ""),
                            image_url=data.get("imageUrl", ""),
                            prompt=request.prompt,
                            model=request.model,
                            width=request.width,
                            height=request.height,
                            generation_time=0.0,  # Not available in REST
                            cost=0.0006
                        )
                    else:
                        logger.error(f"REST API error: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error in REST generation: {e}")
            return None
    
    async def generate_image(
        self, 
        prompt: str,
        style: str = "cinematic",
        aspect_ratio: str = "16:9",
        negative_prompt: str = "",
        progress_callback: Optional[Callable] = None
    ) -> Optional[GenerationResult]:
        """
        Generate image with style and aspect ratio presets
        """
        # Get model for style
        model = self.style_models.get(style, "runware:100@1")
        
        # Get dimensions for aspect ratio
        width, height = self.aspect_ratios.get(aspect_ratio, (1920, 1080))
        
        # Build prompt with style enhancement
        enhanced_prompt = self._enhance_prompt(prompt, style)
        
        request = GenerationRequest(
            prompt=enhanced_prompt,
            width=width,
            height=height,
            model=model,
            negative_prompt=negative_prompt
        )
        
        # Try WebSocket first, fallback to REST
        try:
            result = await self.generate_image_websocket(request, progress_callback)
            if result:
                return result
        except Exception as e:
            logger.warning(f"WebSocket failed, trying REST: {e}")
        
        return await self.generate_image_rest(request)
    
    def _enhance_prompt(self, prompt: str, style: str) -> str:
        """Enhance prompt with style-specific keywords"""
        style_enhancements = {
            "cinematic": "cinematic lighting, professional photography, high quality, detailed",
            "documentary": "documentary style, natural lighting, authentic, realistic",
            "social_media": "trending, viral, eye-catching, modern, high contrast",
            "artistic": "artistic, creative, unique, stylized, beautiful composition",
            "realistic": "photorealistic, detailed, high resolution, professional",
            "cartoon": "cartoon style, animated, colorful, fun, stylized"
        }
        
        enhancement = style_enhancements.get(style, "")
        if enhancement:
            return f"{prompt}, {enhancement}"
        return prompt
    
    async def generate_batch(
        self, 
        prompt: str, 
        count: int = 4,
        style: str = "cinematic",
        aspect_ratio: str = "16:9"
    ) -> List[GenerationResult]:
        """
        Generate multiple variations of an image
        """
        results = []
        
        # Create tasks for parallel generation
        tasks = []
        for i in range(count):
            # Slightly vary the prompt for diversity
            varied_prompt = f"{prompt} variation {i+1}"
            task = self.generate_image(varied_prompt, style, aspect_ratio)
            tasks.append(task)
        
        # Execute all tasks concurrently
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in batch_results:
            if isinstance(result, GenerationResult):
                results.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Batch generation error: {result}")
        
        return results
    
    async def upscale_image(self, image_url: str, upscale_factor: int = 4) -> Optional[str]:
        """
        Upscale an image using Runware's upscaling service
        """
        if not self.api_key:
            logger.error("Runware API key not configured")
            return None
        
        try:
            payload = {
                "taskType": "imageUpscale",
                "taskUUID": f"upscale_{asyncio.get_event_loop().time()}",
                "inputImage": image_url,
                "upscaleFactor": upscale_factor
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.rest_url}/upscale",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("upscaledImageUrl", "")
                    else:
                        logger.error(f"Upscaling error: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error in upscaling: {e}")
            return None 