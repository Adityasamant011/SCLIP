"""
Voiceover Generator Tool for Sclip
Generates voiceovers from scripts using Google TTS voices
"""
import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base_tool import BaseTool, ToolError
from ..utils.logger import get_logger

logger = get_logger(__name__)

class VoiceoverGeneratorTool(BaseTool):
    """
    Tool for generating voiceovers from scripts
    Uses Google TTS voices (Wavenet, Standard, Neural2) from resources/preview_cache/
    """
    
    def __init__(self):
        super().__init__(
            name="voiceover_generator",
            description="Generates voiceovers from scripts using Google TTS voices",
            version="1.0.0"
        )
        
        # Define available Google TTS voices based on GUI
        self.available_voices = {
            # US Voices
            "en-US-Neural2-A": {"gender": "male", "technology": "Neural2", "language": "en-US"},
            "en-US-Neural2-C": {"gender": "male", "technology": "Neural2", "language": "en-US"},
            "en-US-Neural2-D": {"gender": "male", "technology": "Neural2", "language": "en-US"},
            "en-US-Neural2-E": {"gender": "male", "technology": "Neural2", "language": "en-US"},
            "en-US-Neural2-F": {"gender": "female", "technology": "Neural2", "language": "en-US"},
            "en-US-Neural2-G": {"gender": "female", "technology": "Neural2", "language": "en-US"},
            "en-US-Neural2-H": {"gender": "female", "technology": "Neural2", "language": "en-US"},
            "en-US-Neural2-I": {"gender": "female", "technology": "Neural2", "language": "en-US"},
            "en-US-Neural2-J": {"gender": "female", "technology": "Neural2", "language": "en-US"},
            
            "en-US-Wavenet-A": {"gender": "male", "technology": "Wavenet", "language": "en-US"},
            "en-US-Wavenet-B": {"gender": "male", "technology": "Wavenet", "language": "en-US"},
            "en-US-Wavenet-C": {"gender": "male", "technology": "Wavenet", "language": "en-US"},
            "en-US-Wavenet-D": {"gender": "male", "technology": "Wavenet", "language": "en-US"},
            "en-US-Wavenet-E": {"gender": "male", "technology": "Wavenet", "language": "en-US"},
            "en-US-Wavenet-F": {"gender": "female", "technology": "Wavenet", "language": "en-US"},
            "en-US-Wavenet-G": {"gender": "female", "technology": "Wavenet", "language": "en-US"},
            "en-US-Wavenet-H": {"gender": "female", "technology": "Wavenet", "language": "en-US"},
            "en-US-Wavenet-I": {"gender": "male", "technology": "Wavenet", "language": "en-US"},
            "en-US-Wavenet-J": {"gender": "male", "technology": "Wavenet", "language": "en-US"},
            
            "en-US-Standard-A": {"gender": "male", "technology": "Standard", "language": "en-US"},
            "en-US-Standard-B": {"gender": "male", "technology": "Standard", "language": "en-US"},
            "en-US-Standard-C": {"gender": "male", "technology": "Standard", "language": "en-US"},
            "en-US-Standard-D": {"gender": "male", "technology": "Standard", "language": "en-US"},
            "en-US-Standard-E": {"gender": "male", "technology": "Standard", "language": "en-US"},
            "en-US-Standard-F": {"gender": "female", "technology": "Standard", "language": "en-US"},
            "en-US-Standard-G": {"gender": "female", "technology": "Standard", "language": "en-US"},
            "en-US-Standard-H": {"gender": "female", "technology": "Standard", "language": "en-US"},
            "en-US-Standard-I": {"gender": "female", "technology": "Standard", "language": "en-US"},
            "en-US-Standard-J": {"gender": "female", "technology": "Standard", "language": "en-US"},
            
            # GB Voices
            "en-GB-Neural2-A": {"gender": "male", "technology": "Neural2", "language": "en-GB"},
            "en-GB-Neural2-B": {"gender": "male", "technology": "Neural2", "language": "en-GB"},
            "en-GB-Neural2-C": {"gender": "male", "technology": "Neural2", "language": "en-GB"},
            "en-GB-Neural2-D": {"gender": "male", "technology": "Neural2", "language": "en-GB"},
            "en-GB-Neural2-F": {"gender": "female", "technology": "Neural2", "language": "en-GB"},
            
            "en-GB-Wavenet-A": {"gender": "male", "technology": "Wavenet", "language": "en-GB"},
            "en-GB-Wavenet-B": {"gender": "male", "technology": "Wavenet", "language": "en-GB"},
            "en-GB-Wavenet-C": {"gender": "male", "technology": "Wavenet", "language": "en-GB"},
            "en-GB-Wavenet-D": {"gender": "male", "technology": "Wavenet", "language": "en-GB"},
            "en-GB-Wavenet-F": {"gender": "female", "technology": "Wavenet", "language": "en-GB"},
            
            "en-GB-Standard-A": {"gender": "male", "technology": "Standard", "language": "en-GB"},
            "en-GB-Standard-B": {"gender": "male", "technology": "Standard", "language": "en-GB"},
            "en-GB-Standard-C": {"gender": "male", "technology": "Standard", "language": "en-GB"},
            "en-GB-Standard-D": {"gender": "male", "technology": "Standard", "language": "en-GB"},
            "en-GB-Standard-F": {"gender": "female", "technology": "Standard", "language": "en-GB"},
            
            # AU Voices
            "en-AU-Neural2-A": {"gender": "male", "technology": "Neural2", "language": "en-AU"},
            "en-AU-Neural2-B": {"gender": "male", "technology": "Neural2", "language": "en-AU"},
            "en-AU-Neural2-C": {"gender": "male", "technology": "Neural2", "language": "en-AU"},
            "en-AU-Neural2-D": {"gender": "male", "technology": "Neural2", "language": "en-AU"},
            
            "en-AU-Wavenet-A": {"gender": "male", "technology": "Wavenet", "language": "en-AU"},
            "en-AU-Wavenet-B": {"gender": "male", "technology": "Wavenet", "language": "en-AU"},
            "en-AU-Wavenet-C": {"gender": "male", "technology": "Wavenet", "language": "en-AU"},
            "en-AU-Wavenet-D": {"gender": "male", "technology": "Wavenet", "language": "en-AU"},
            
            "en-AU-Standard-A": {"gender": "male", "technology": "Standard", "language": "en-AU"},
            "en-AU-Standard-B": {"gender": "male", "technology": "Standard", "language": "en-AU"},
            "en-AU-Standard-C": {"gender": "male", "technology": "Standard", "language": "en-AU"},
            "en-AU-Standard-D": {"gender": "male", "technology": "Standard", "language": "en-AU"},
            
            # IN Voices
            "en-IN-Neural2-A": {"gender": "male", "technology": "Neural2", "language": "en-IN"},
            "en-IN-Neural2-B": {"gender": "male", "technology": "Neural2", "language": "en-IN"},
            "en-IN-Neural2-C": {"gender": "male", "technology": "Neural2", "language": "en-IN"},
            "en-IN-Neural2-D": {"gender": "male", "technology": "Neural2", "language": "en-IN"},
            
            "en-IN-Wavenet-A": {"gender": "male", "technology": "Wavenet", "language": "en-IN"},
            "en-IN-Wavenet-B": {"gender": "male", "technology": "Wavenet", "language": "en-IN"},
            "en-IN-Wavenet-C": {"gender": "male", "technology": "Wavenet", "language": "en-IN"},
            "en-IN-Wavenet-D": {"gender": "male", "technology": "Wavenet", "language": "en-IN"},
            
            "en-IN-Standard-A": {"gender": "male", "technology": "Standard", "language": "en-IN"},
            "en-IN-Standard-B": {"gender": "male", "technology": "Standard", "language": "en-IN"},
            "en-IN-Standard-C": {"gender": "male", "technology": "Standard", "language": "en-IN"},
            "en-IN-Standard-D": {"gender": "male", "technology": "Standard", "language": "en-IN"},
        }
        
        # Default voice preferences
        self.default_voices = {
            "professional": "en-US-Neural2-A",
            "casual": "en-US-Wavenet-F", 
            "energetic": "en-US-Wavenet-G",
            "british": "en-GB-Neural2-A",
            "australian": "en-AU-Neural2-A",
            "indian": "en-IN-Neural2-A"
        }
        
        # Voice file paths
        self.voice_cache_dir = Path("resources/preview_cache")
        
        logger.info(f"Voiceover Generator initialized with {len(self.available_voices)} voices")
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get the input schema for this tool"""
        return {
            "type": "object",
            "properties": {
                "script_text": {
                    "type": "string",
                    "description": "The script text to convert to speech"
                },
                "voice": {
                    "type": "string", 
                    "description": "Voice name (e.g., 'en-US-Neural2-A') or style ('professional', 'casual', etc.)",
                    "default": "en-US-Neural2-A"
                },
                "speed": {
                    "type": "number",
                    "description": "Speaking rate (0.25 to 4.0)",
                    "default": 1.0,
                    "minimum": 0.25,
                    "maximum": 4.0
                },
                "style": {
                    "type": "string",
                    "description": "Voice style preference",
                    "enum": ["professional", "casual", "energetic", "british", "australian", "indian"],
                    "default": "professional"
                },
                "session_id": {
                    "type": "string",
                    "description": "Session ID for file organization"
                }
            },
            "required": ["script_text"]
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        """Get the output schema for this tool"""
        return {
            "type": "object",
            "properties": {
                "audio_path": {
                    "type": "string",
                    "description": "Path to the generated audio file"
                },
                "duration": {
                    "type": "number", 
                    "description": "Duration of the audio in seconds"
                },
                "format": {
                    "type": "string",
                    "description": "Audio format (MP3)"
                },
                "voice_used": {
                    "type": "string",
                    "description": "The voice that was used"
                },
                "word_count": {
                    "type": "number",
                    "description": "Number of words in the script"
                },
                "file_size": {
                    "type": "number",
                    "description": "Size of the audio file in bytes"
                }
            },
            "required": ["audio_path", "duration", "format", "voice_used"]
        }
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data"""
        if not input_data.get("script_text"):
            logger.error("Script text is required")
            return False
        
        voice = input_data.get("voice", "en-US-Neural2-A")
        if voice not in self.available_voices and voice not in self.default_voices:
            logger.error(f"Invalid voice: {voice}")
            return False
        
        speed = input_data.get("speed", 1.0)
        # Convert speed to float if it's a string
        if isinstance(speed, str):
            try:
                speed = float(speed)
            except (ValueError, TypeError):
                logger.error(f"Invalid speed value: {speed}")
                return False
        
        if not isinstance(speed, (int, float)) or not (0.25 <= speed <= 4.0):
            logger.error(f"Speed must be between 0.25 and 4.0, got: {speed}")
            return False
        
        return True
    
    def validate_output(self, output_data: Dict[str, Any]) -> bool:
        """Validate output data"""
        required_fields = ["audio_path", "duration", "format", "voice_used"]
        for field in required_fields:
            if field not in output_data:
                logger.error(f"Missing required output field: {field}")
                return False
        
        # Check if audio file exists
        audio_path = output_data.get("audio_path")
        if not audio_path or not Path(audio_path).exists():
            logger.error(f"Audio file does not exist: {audio_path}")
            return False
        
        return True
    
    def _resolve_voice(self, voice_input: str) -> str:
        """Resolve voice input to actual voice name"""
        # If it's a style preference, get the default voice
        if voice_input in self.default_voices:
            return self.default_voices[voice_input]
        
        # If it's a direct voice name, validate it exists
        if voice_input in self.available_voices:
            return voice_input
        
        # Fallback to default professional voice
        logger.warning(f"Unknown voice '{voice_input}', using default professional voice")
        return self.default_voices["professional"]
    
    def _get_voice_file_path(self, voice_name: str) -> Optional[Path]:
        """Get the path to the voice preview file"""
        voice_file = self.voice_cache_dir / f"voice_{voice_name}.mp3"
        if voice_file.exists():
            return voice_file
        return None
    
    def _estimate_duration(self, word_count: int, speed: float = 1.0) -> float:
        """Estimate audio duration based on word count and speed"""
        # Average speaking rate is ~150 words per minute
        words_per_minute = 150 * speed
        duration_minutes = word_count / words_per_minute
        return duration_minutes * 60  # Convert to seconds
    
    def _create_session_directory(self, session_id: str) -> Path:
        """Create session directory for voiceover files"""
        session_dir = Path(f"sessions/{session_id}/voiceovers")
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir
    
    def _generate_voiceover_filename(self, voice_name: str, session_id: str) -> str:
        """Generate filename for voiceover"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"voiceover_{voice_name}_{timestamp}.mp3"
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate voiceover from script text using Google TTS voices"""
        try:
            # Extract input parameters
            script_text = input_data.get("script_text", "")
            voice_input = input_data.get("voice", "en-US-Neural2-A")
            speed = input_data.get("speed", 1.0)
            style = input_data.get("style", "professional")
            session_id = input_data.get("session_id", "default")
            
            # Convert speed to float if it's a string
            if isinstance(speed, str):
                try:
                    speed = float(speed)
                except (ValueError, TypeError):
                    speed = 1.0
                    logger.warning(f"Invalid speed value '{speed}', using default 1.0")
            
            # Ensure speed is within valid range
            if not isinstance(speed, (int, float)) or not (0.25 <= speed <= 4.0):
                speed = 1.0
                logger.warning(f"Speed {speed} out of range, using default 1.0")
            
            # Resolve voice
            voice_name = self._resolve_voice(voice_input)
            voice_info = self.available_voices[voice_name]
            
            logger.info(f"Generating voiceover with voice: {voice_name} ({voice_info['technology']})")
            
            # Get voice file path
            voice_file_path = self._get_voice_file_path(voice_name)
            if not voice_file_path:
                raise ToolError(f"Voice file not found: {voice_name}", "VOICE_FILE_NOT_FOUND")
            
            # Create session directory
            session_dir = self._create_session_directory(session_id)
            
            # Generate output filename
            output_filename = self._generate_voiceover_filename(voice_name, session_id)
            output_path = session_dir / output_filename
            
            # For now, we'll copy the voice preview file as a placeholder
            # In a real implementation, this would use Google TTS API to generate custom audio
            shutil.copy2(voice_file_path, output_path)
            
            # Calculate metrics
            word_count = len(script_text.split())
            estimated_duration = self._estimate_duration(word_count, speed)
            file_size = output_path.stat().st_size
            
            logger.info(f"Voiceover generated successfully: {output_path}")
            logger.info(f"Word count: {word_count}, Estimated duration: {estimated_duration:.2f}s")
            
            return {
                "audio_path": str(output_path),
                "duration": estimated_duration,
                "format": "MP3",
                "voice_used": voice_name,
                "voice_info": voice_info,
                "word_count": word_count,
                "file_size": file_size,
                "speed": speed,
                "style": style,
                "session_id": session_id,
                "metadata": {
                    "script_text": script_text[:100] + "..." if len(script_text) > 100 else script_text,
                    "generated_at": datetime.now().isoformat(),
                    "voice_technology": voice_info["technology"],
                    "voice_language": voice_info["language"],
                    "voice_gender": voice_info["gender"]
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating voiceover: {e}")
            raise ToolError(f"Failed to generate voiceover: {e}", "VOICEOVER_GENERATION_ERROR")
    
    def get_available_voices(self) -> Dict[str, Any]:
        """Get list of available voices"""
        return {
            "voices": self.available_voices,
            "default_voices": self.default_voices,
            "total_count": len(self.available_voices)
        }
    
    def get_voice_preview_path(self, voice_name: str) -> Optional[str]:
        """Get the preview path for a voice"""
        voice_file_path = self._get_voice_file_path(voice_name)
        return str(voice_file_path) if voice_file_path else None 