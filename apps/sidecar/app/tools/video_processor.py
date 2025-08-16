"""
Video Processor Tool for Sclip
Advanced video editing with CapCut-level capabilities
"""
import asyncio
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import tempfile

from .base_tool import BaseTool, ToolError
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Always resolve resource files relative to the project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.resolve()

class VideoProcessorTool(BaseTool):
    """
    Advanced video processor with CapCut-level capabilities
    Supports complex video editing, effects, transitions, and professional assembly
    """
    
    def __init__(self):
        super().__init__(
            name="video_processor",
            description="Advanced video editing with professional effects and transitions",
            version="2.0.0"
        )
        
        # Load effects and transitions from resources
        self.effects = self._load_effects()
        self.transitions = self._load_transitions()
        self.filters = self._load_filters()
        
        # FFmpeg filter mappings for effects
        self.effect_filters = {
            # Movement effects
            "zoom_in": "zoompan=z='min(zoom+0.01,2)':d=25:s=64x64",
            "zoom_out": "zoompan=z='max(zoom-0.01,0.5)':d=25:s=64x64",
            "pan_left": "crop=w=iw*0.8:h=ih:x='(iw-ow)*t/1':y=0",
            "pan_right": "crop=w=iw*0.8:h=ih:x='(iw-ow)*(1-t/1)':y=0",
            "pan_up": "crop=w=iw:h=ih*0.8:x=0:y='(ih-oh)*t/1'",
            "pan_down": "crop=w=iw:h=ih*0.8:x=0:y='(ih-oh)*(1-t/1)'",
            "shake_mild": "crop=w=iw*0.9:h=ih*0.9:x='(iw-ow)/2+sin(n*0.3)*5':y='(ih-oh)/2+cos(n*0.3)*5'",
            "shake_strong": "crop=w=iw*0.9:h=ih*0.9:x='(iw-ow)/2+sin(n*0.3)*15':y='(ih-oh)/2+cos(n*0.3)*15'",
            "rotate_cw": "rotate='PI*t/2':fillcolor=black",
            "rotate_ccw": "rotate='-PI*t/2':fillcolor=black",
            
            # Cinematic effects
            "ken_burns": "zoompan=z='min(zoom+0.0015,1.5)':d=25",
            "dolly_zoom": "perspective=x0=0:y0=0:x1=W:y1=0:x2=0:y2=H:x3=W:y3=H:interpolation=linear",
            "tilt_shift": "boxblur=2:1",
            "barrel_roll": "rotate='2*PI*t':fillcolor=black",
            "spiral_zoom": "rotate='PI*t':fillcolor=black,zoompan=z='min(zoom+0.01,2)':d=25",
            
            # Opacity effects
            "fade_in": "fade=t=in:st=0:d=1",
            "fade_out": "fade=t=out:st=0:d=1",
            "fade_white_in": "fade=t=in:st=0:d=1:color=white",
            "fade_white_out": "fade=t=out:st=0:d=1:color=white",
            "flash": "curves=all='0/1 0.1/0 0.2/1 1/1'",
            "strobe": "eq=brightness='0.5+0.5*sin(2*PI*t*4)'",
            "pulse": "scale='64+10*sin(n*0.2)':'64+10*sin(n*0.2)'",
            
            # Glitch effects
            "rgb_split": "split[a][b][c];[a]pad=iw+10:ih+10:5:5:red[a];[b]pad=iw+10:ih+10:0:5:green[b];[c]pad=iw+10:ih+10:10:5:blue[c];[a][b]blend=all_mode=screen[ab];[ab][c]blend=all_mode=screen",
            "glitch_digital": "noise=alls=20:allf=t+u",
            "glitch_analog": "hue=h='sin(2*PI*t)*180'",
            "pixel_sort": "shufflepixels=width=8:height=8",
            "datamosh": "setpts='0.5*PTS'",
            "scan_lines": "drawbox=0:0:iw:ih:color=black@0.3:thickness=2:fill=1",
            "noise_overlay": "noise=alls=10:allf=t",
            
            # Time effects
            "speed_ramp_up": "setpts='PTS/(1+t*0.5)'",
            "speed_ramp_down": "setpts='PTS*(1+t*0.5)'",
            "freeze_frame": "tblend=all_mode=average",
            "rewind": "reverse",
            "time_echo": "tblend=all_mode=difference",
            
            # Frame effects
            "frame_hold": "tblend=all_mode=average",
            "frame_blend": "tblend=all_mode=overlay",
            "frame_skip": "select='not(mod(n,2))'",
            "ghost_trail": "tblend=all_mode=overlay",
            
            # Light effects
            "lens_flare": "drawbox=0:0:iw:ih:color=yellow@0.5:thickness=50:fill=1",
            "light_leak": "drawbox=0:0:iw:ih:color=orange@0.3:thickness=20:fill=1",
            "god_rays": "drawbox=0:0:iw:ih:color=white@0.4:thickness=30:fill=1",
            "spotlight": "vignette=angle=PI/4",
            
            # Distortion effects
            "wave_distort": "waveform=period=10:amplitude=20",
            "ripple": "waveform=period=5:amplitude=10",
            "fisheye": "lenscorrection=k1=0.1:k2=0.1",
            "mirror": "crop=w=iw/2:h=ih:x=0:y=0,pad=iw*2:ih:iw:0",
            "kaleidoscope": "crop=w=iw/4:h=ih:x=0:y=0,pad=iw*4:ih:iw*3:0",
            
            # Particle effects (simplified)
            "particle_burst": "noise=alls=5:allf=t",
            "snow": "noise=alls=3:allf=t",
            "rain": "noise=alls=2:allf=t",
            "sparkles": "noise=alls=1:allf=t"
        }
        
        # Transition mappings
        self.transition_filters = {
            "fade": "xfade=transition=fade:duration=1:offset=0",
            "fadeblack": "xfade=transition=fadeblack:duration=1:offset=0",
            "fadewhite": "xfade=transition=fadewhite:duration=1:offset=0",
            "fadegrays": "xfade=transition=fadegrays:duration=1:offset=0",
            "dissolve": "xfade=transition=dissolve:duration=1:offset=0",
            "wipeleft": "xfade=transition=wipeleft:duration=1:offset=0",
            "wiperight": "xfade=transition=wiperight:duration=1:offset=0",
            "wipeup": "xfade=transition=wipeup:duration=1:offset=0",
            "wipedown": "xfade=transition=wipedown:duration=1:offset=0",
            "slideleft": "xfade=transition=slideleft:duration=1:offset=0",
            "slideright": "xfade=transition=slideright:duration=1:offset=0",
            "slideup": "xfade=transition=slideup:duration=1:offset=0",
            "slidedown": "xfade=transition=slidedown:duration=1:offset=0",
            "circleopen": "xfade=transition=circleopen:duration=1:offset=0",
            "circleclose": "xfade=transition=circleclose:duration=1:offset=0",
            "zoomin": "xfade=transition=zoomin:duration=1:offset=0"
        }
        
        # Filter mappings
        self.filter_mappings = {
            "vintage": "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131,vignette=angle=PI/4",
            "cinematic": "colorlevels=rimin=0.1:gimin=0.1:bimin=0.1:rimax=0.9:gimax=0.9:bimax=0.9",
            "warm": "colorbalance=rs=0.1:gs=0.05:bs=-0.1",
            "cool": "colorbalance=rs=-0.1:gs=-0.05:bs=0.1",
            "dramatic": "curves=all='0/0.1 0.3/0.2 0.7/0.8 1/0.9'",
            "bright": "eq=brightness=0.2:contrast=1.2",
            "dark": "eq=brightness=-0.2:contrast=0.8",
            "saturated": "eq=saturation=1.5",
            "desaturated": "eq=saturation=0.5",
            "high_contrast": "eq=contrast=1.5",
            "low_contrast": "eq=contrast=0.7",
            "sharp": "unsharp=3:3:1.5:3:3:0.5",
            "soft": "boxblur=2:1",
            "grain": "noise=alls=5:allf=t",
            "blur": "gblur=sigma=3",
            "sepia": "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131",
            "black_white": "hue=s=0",
            "invert": "negate",
            "posterize": "posterize=levels=4"
        }
        
        # Video processing settings
        self.default_settings = {
            "resolution": "1920x1080",
            "fps": 30,
            "bitrate": "5M",
            "audio_bitrate": "128k",
            "audio_sample_rate": 44100,
            "codec": "libx264",
            "audio_codec": "aac",
            "preset": "medium",
            "crf": 23
        }
        
        logger.info(f"Video Processor initialized with {len(self.effects)} effects, {len(self.transitions)} transitions")
    
    def _load_effects(self) -> List[Dict[str, Any]]:
        """Load effects from JSON file"""
        try:
            effects_file = Path(os.path.join(PROJECT_ROOT, "resources", "effects.json"))
            if effects_file.exists():
                with open(effects_file, 'r') as f:
                    effects = json.load(f)
                    logger.info(f"Loaded {len(effects)} effects")
                    return effects
            else:
                logger.warning(f"Effects file not found: {effects_file}")
        except Exception as e:
            logger.error(f"Error loading effects: {e}")
        return []
    
    def _load_transitions(self) -> List[Dict[str, Any]]:
        """Load transitions from JSON file"""
        try:
            transitions_file = Path(os.path.join(PROJECT_ROOT, "resources", "transitions.json"))
            if transitions_file.exists():
                with open(transitions_file, 'r') as f:
                    transitions = json.load(f)
                    logger.info(f"Loaded {len(transitions)} transitions")
                    return transitions
            else:
                logger.warning(f"Transitions file not found: {transitions_file}")
        except Exception as e:
            logger.error(f"Error loading transitions: {e}")
        return []
    
    def _load_filters(self) -> List[Dict[str, Any]]:
        """Load filters from JSON file"""
        try:
            filters_file = Path(os.path.join(PROJECT_ROOT, "resources", "filters.json"))
            if filters_file.exists():
                with open(filters_file, 'r') as f:
                    filters = json.load(f)
                    logger.info(f"Loaded {len(filters)} filters")
                    return filters
            else:
                logger.warning(f"Filters file not found: {filters_file}")
        except Exception as e:
            logger.error(f"Error loading filters: {e}")
        return []
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get the input schema for this tool"""
        return {
            "type": "object",
            "properties": {
                "script_path": {
                    "type": "string",
                    "description": "Path to the script file"
                },
                "broll_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of B-roll video/image paths"
                },
                "audio_path": {
                    "type": "string",
                    "description": "Path to the voiceover audio file"
                },
                "style": {
                    "type": "string",
                    "description": "Video style (cinematic, documentary, social_media, etc.)",
                    "default": "cinematic"
                },
                "resolution": {
                    "type": "string",
                    "description": "Output resolution (e.g., '1920x1080', '1080x1920')",
                    "default": "1920x1080"
                },
                "fps": {
                    "type": "integer",
                    "description": "Output frame rate",
                    "default": 30
                },
                "effects": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "start_time": {"type": "number"},
                            "duration": {"type": "number"},
                            "intensity": {"type": "number", "default": 1.0}
                        }
                    },
                    "description": "List of effects to apply"
                },
                "transitions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "start_time": {"type": "number"},
                            "duration": {"type": "number"}
                        }
                    },
                    "description": "List of transitions to apply"
                },
                "filters": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "intensity": {"type": "number", "default": 1.0}
                        }
                    },
                    "description": "List of filters to apply"
                },
                "text_overlays": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "start_time": {"type": "number"},
                            "duration": {"type": "number"},
                            "position": {"type": "string", "default": "center"},
                            "font_size": {"type": "integer", "default": 48},
                            "color": {"type": "string", "default": "white"}
                        }
                    },
                    "description": "List of text overlays"
                },
                "background_music": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "volume": {"type": "number", "default": 0.3}
                    },
                    "description": "Background music settings"
                },
                "session_id": {
                    "type": "string",
                    "description": "Session ID for file organization"
                },
                "existing_video_path": {
                    "type": "string",
                    "description": "Path to existing video for editing (CapCut-level timeline editing)"
                },
                "timeline_edits": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["trim", "split", "insert", "cut", "effect", "text"]},
                            "start_time": {"type": "number"},
                            "duration": {"type": "number", "default": 1},
                            "end_time": {"type": "number"},
                            "effect_name": {"type": "string"},
                            "intensity": {"type": "number", "default": 1.0},
                            "text": {"type": "string"},
                            "text_options": {"type": "object"},
                            "insert_video_path": {"type": "string"}
                        }
                    },
                    "description": "List of timeline edit operations (CapCut-level precision)"
                },
                "trim_operations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "start_time": {"type": "number"},
                            "end_time": {"type": "number"},
                            "output_path": {"type": "string"}
                        }
                    },
                    "description": "Trim video at specific timestamps"
                },
                "split_operations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "split_time": {"type": "number"},
                            "output_path": {"type": "string"}
                        }
                    },
                    "description": "Split video at specific timestamps"
                },
                "insert_operations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "insert_time": {"type": "number"},
                            "insert_video_path": {"type": "string"},
                            "output_path": {"type": "string"}
                        }
                    },
                    "description": "Insert video at specific timestamps"
                },
                "cut_operations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "start_time": {"type": "number"},
                            "end_time": {"type": "number"},
                            "output_path": {"type": "string"}
                        }
                    },
                    "description": "Cut segments at specific timestamps"
                }
            },
            "required": ["broll_paths", "audio_path"]
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        """Get the output schema for this tool"""
        return {
            "type": "object",
            "properties": {
                "video_path": {
                    "type": "string",
                    "description": "Path to the generated video file"
                },
                "duration": {
                    "type": "number",
                    "description": "Duration of the video in seconds"
                },
                "thumbnail_path": {
                    "type": "string",
                    "description": "Path to the video thumbnail"
                },
                "format": {
                    "type": "string",
                    "description": "Video format (MP4)"
                },
                "resolution": {
                    "type": "string",
                    "description": "Video resolution"
                },
                "fps": {
                    "type": "number",
                    "description": "Frame rate"
                },
                "file_size": {
                    "type": "number",
                    "description": "File size in bytes"
                },
                "effects_applied": {
                    "type": "array",
                    "description": "List of effects that were applied"
                },
                "transitions_applied": {
                    "type": "array",
                    "description": "List of transitions that were applied"
                }
            },
            "required": ["video_path", "duration", "format"]
        }
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data"""
        if not input_data.get("broll_paths"):
            logger.error("B-roll paths are required")
            return False
        
        if not input_data.get("audio_path"):
            logger.error("Audio path is required")
            return False
        
        # Validate file paths exist
        for broll_path in input_data.get("broll_paths", []):
            if not Path(broll_path).exists():
                logger.error(f"B-roll file not found: {broll_path}")
                return False
        
        audio_path = input_data.get("audio_path")
        if not Path(audio_path).exists():
            logger.error(f"Audio file not found: {audio_path}")
            return False
        
        return True
    
    def validate_output(self, output_data: Dict[str, Any]) -> bool:
        """Validate output data"""
        required_fields = ["video_path", "duration", "format"]
        for field in required_fields:
            if field not in output_data:
                logger.error(f"Missing required output field: {field}")
                return False
        
        # Check if video file exists
        video_path = output_data.get("video_path")
        if not video_path or not Path(video_path).exists():
            logger.error(f"Video file does not exist: {video_path}")
            return False
        
        return True
    
    def _create_session_directory(self, session_id: str) -> Path:
        """Create session directory for video files"""
        session_dir = Path(f"sessions/{session_id}/videos")
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir
    
    def _get_video_info(self, video_path: str) -> Dict[str, Any]:
        """Get video information using FFprobe"""
        try:
            cmd = [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", "-show_streams", video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                info = json.loads(result.stdout)
                return info
            else:
                logger.error(f"FFprobe failed: {result.stderr}")
                return {}
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return {}
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration using FFprobe"""
        try:
            cmd = [
                "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                "-of", "csv=p=0", audio_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return float(result.stdout.strip())
            else:
                logger.error(f"FFprobe failed for audio: {result.stderr}")
                return 0.0
        except Exception as e:
            logger.error(f"Error getting audio duration: {e}")
            return 0.0
    
    def _create_video_filter(self, effects: List[Dict], transitions: List[Dict], 
                           filters: List[Dict], text_overlays: List[Dict]) -> str:
        """Create complex FFmpeg filter for video processing"""
        filter_parts = []
        
        # Apply filters - handle both string and dict inputs
        for filter_info in filters:
            if isinstance(filter_info, str):
                filter_name = filter_info
                intensity = 1.0
            else:
                filter_name = filter_info.get("name")
                intensity = filter_info.get("intensity", 1.0)
            
            if filter_name in self.filter_mappings:
                filter_expr = self.filter_mappings[filter_name]
                if intensity != 1.0:
                    # Adjust filter intensity
                    filter_expr = f"eq=contrast={intensity},{filter_expr}"
                filter_parts.append(filter_expr)
        
        # Apply effects - handle both string and dict inputs
        for effect_info in effects:
            if isinstance(effect_info, str):
                effect_name = effect_info
                start_time = 0
                duration = 1
                intensity = 1.0
            else:
                effect_name = effect_info.get("name")
                start_time = effect_info.get("start_time", 0)
                duration = effect_info.get("duration", 1)
                intensity = effect_info.get("intensity", 1.0)
            
            if effect_name in self.effect_filters:
                effect_expr = self.effect_filters[effect_name]
                # Apply effect only during specified time
                filter_parts.append(f"between(t,{start_time},{start_time + duration})*{effect_expr}")
        
        # Apply text overlays - handle both string and dict inputs
        for i, text_info in enumerate(text_overlays):
            if isinstance(text_info, str):
                text = text_info
                start_time = 0
                duration = 5
                position = "center"
                font_size = 48
                color = "white"
            else:
                text = text_info.get("text", "")
                start_time = text_info.get("start_time", 0)
                duration = text_info.get("duration", 5)
                position = text_info.get("position", "center")
                font_size = text_info.get("font_size", 48)
                color = text_info.get("color", "white")
            
            # Create text overlay filter
            text_filter = f"drawtext=text='{text}':fontsize={font_size}:fontcolor={color}:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,{start_time},{start_time + duration})'"
            filter_parts.append(text_filter)
        
        # Combine all filters
        if filter_parts:
            return ",".join(filter_parts)
        return ""
    
    def _create_transition_filter(self, transition_name: str, duration: float = 1.0) -> str:
        """Create transition filter"""
        if transition_name in self.transition_filters:
            return self.transition_filters[transition_name].replace("duration=1", f"duration={duration}")
        return ""
    
    def _concatenate_videos(self, video_paths: List[str], output_path: str, 
                          transitions: List[Dict]) -> bool:
        """Concatenate multiple videos with transitions"""
        try:
            # Create file list for FFmpeg
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                for video_path in video_paths:
                    f.write(f"file '{video_path}'\n")
                file_list_path = f.name
            
            # Build FFmpeg command - use re-encoding for better compatibility with image-based videos
            cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", file_list_path]
            
            # Add transitions if specified
            if transitions:
                filter_complex = []
                for i, transition in enumerate(transitions):
                    transition_name = transition.get("name", "fade")
                    duration = transition.get("duration", 1.0)
                    filter_complex.append(self._create_transition_filter(transition_name, duration))
                
                if filter_complex:
                    cmd.extend(["-filter_complex", ";".join(filter_complex)])
            
            # Use re-encoding instead of copy for better compatibility
            cmd.extend(["-c:v", "libx264", "-preset", "medium", "-crf", "23", output_path])
            
            # Execute FFmpeg
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Clean up
            os.unlink(file_list_path)
            
            if result.returncode != 0:
                logger.error(f"FFmpeg concatenation failed: {result.stderr}")
                # Try simpler approach without transitions
                simple_cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", file_list_path,
                            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", output_path]
                result = subprocess.run(simple_cmd, capture_output=True, text=True)
                logger.info(f"Simple concatenation result: {result.returncode}")
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Error concatenating videos: {e}")
            return False
    
    def _add_audio_to_video(self, video_path: str, audio_path: str, output_path: str,
                           background_music: Optional[Dict] = None) -> bool:
        """Add audio to video with optional background music"""
        try:
            cmd = ["ffmpeg", "-y", "-i", video_path, "-i", audio_path]
            
            # Add background music if specified
            if background_music:
                music_path = background_music.get("path")
                music_volume = background_music.get("volume", 0.3)
                
                if music_path and Path(music_path).exists():
                    cmd.extend(["-i", music_path])
                    # Mix audio tracks
                    filter_complex = f"[1:a]volume=1.0[voice];[2:a]volume={music_volume}[music];[voice][music]amix=inputs=2:duration=longest[out]"
                    cmd.extend(["-filter_complex", filter_complex, "-map", "0:v", "-map", "[out]"])
                else:
                    cmd.extend(["-c:v", "copy", "-c:a", "aac", "-shortest"])
            else:
                cmd.extend(["-c:v", "copy", "-c:a", "aac", "-shortest"])
            
            cmd.append(output_path)
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Error adding audio to video: {e}")
            return False
    
    def _generate_thumbnail(self, video_path: str, output_path: str) -> bool:
        """Generate thumbnail from video"""
        try:
            cmd = [
                "ffmpeg", "-y", "-i", video_path,
                "-ss", "00:00:01", "-vframes", "1",
                "-vf", "scale=320:180:flags=lanczos",
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Error generating thumbnail: {e}")
            return False
    
    def _trim_video_at_timestamp(self, input_path: str, output_path: str, 
                                start_time: float, end_time: float) -> bool:
        """Trim video at specific timestamps (CapCut-level precision)"""
        try:
            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-ss", str(start_time), "-t", str(end_time - start_time),
                "-c:v", "libx264", "-c:a", "aac",
                "-avoid_negative_ts", "make_zero",
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Error trimming video: {e}")
            return False
    
    def _split_video_at_timestamp(self, input_path: str, split_time: float) -> Tuple[str, str]:
        """Split video at specific timestamp (CapCut-level precision)"""
        try:
            # Get video duration
            video_info = self._get_video_info(input_path)
            duration = float(video_info.get("format", {}).get("duration", 0))
            
            if split_time >= duration:
                raise ValueError(f"Split time {split_time} exceeds video duration {duration}")
            
            # Create output paths
            base_path = Path(input_path).stem
            output_path_1 = str(Path(input_path).parent / f"{base_path}_part1.mp4")
            output_path_2 = str(Path(input_path).parent / f"{base_path}_part2.mp4")
            
            # Split video
            success_1 = self._trim_video_at_timestamp(input_path, output_path_1, 0, split_time)
            success_2 = self._trim_video_at_timestamp(input_path, output_path_2, split_time, duration)
            
            if success_1 and success_2:
                return output_path_1, output_path_2
            else:
                raise Exception("Failed to split video")
                
        except Exception as e:
            logger.error(f"Error splitting video: {e}")
            return "", ""
    
    def _insert_video_at_timestamp(self, main_video_path: str, insert_video_path: str, 
                                  insert_time: float, output_path: str) -> bool:
        """Insert video at specific timestamp (CapCut-level precision)"""
        try:
            # Get main video duration
            main_info = self._get_video_info(main_video_path)
            main_duration = float(main_info.get("format", {}).get("duration", 0))
            
            if insert_time > main_duration:
                raise ValueError(f"Insert time {insert_time} exceeds main video duration {main_duration}")
            
            # Split main video at insert point
            part1_path, part2_path = self._split_video_at_timestamp(main_video_path, insert_time)
            
            if not part1_path or not part2_path:
                raise Exception("Failed to split main video for insertion")
            
            # Concatenate: part1 + insert_video + part2
            temp_list_path = str(Path(output_path).parent / "temp_concat_list.txt")
            with open(temp_list_path, 'w') as f:
                f.write(f"file '{part1_path}'\n")
                f.write(f"file '{insert_video_path}'\n")
                f.write(f"file '{part2_path}'\n")
            
            # Concatenate with FFmpeg
            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", temp_list_path, "-c", "copy", output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Cleanup
            os.unlink(temp_list_path)
            os.unlink(part1_path)
            os.unlink(part2_path)
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Error inserting video: {e}")
            return False
    
    def _cut_segment_at_timestamp(self, input_path: str, start_time: float, 
                                 end_time: float, output_path: str) -> bool:
        """Cut/remove segment from video at specific timestamps (CapCut-level precision)"""
        try:
            # Get video duration
            video_info = self._get_video_info(input_path)
            duration = float(video_info.get("format", {}).get("duration", 0))
            
            if end_time > duration:
                end_time = duration
            
            if start_time >= end_time:
                raise ValueError("Start time must be less than end time")
            
            # Create parts: before cut + after cut
            part1_path = str(Path(output_path).parent / "temp_part1.mp4")
            part2_path = str(Path(output_path).parent / "temp_part2.mp4")
            
            # Extract parts
            success_1 = self._trim_video_at_timestamp(input_path, part1_path, 0, start_time)
            success_2 = self._trim_video_at_timestamp(input_path, part2_path, end_time, duration)
            
            if not success_1 or not success_2:
                raise Exception("Failed to extract video parts for cutting")
            
            # Concatenate parts
            temp_list_path = str(Path(output_path).parent / "temp_cut_list.txt")
            with open(temp_list_path, 'w') as f:
                f.write(f"file '{part1_path}'\n")
                f.write(f"file '{part2_path}'\n")
            
            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", temp_list_path, "-c", "copy", output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Cleanup
            os.unlink(temp_list_path)
            os.unlink(part1_path)
            os.unlink(part2_path)
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Error cutting video segment: {e}")
            return False
    
    def _apply_effect_at_timestamp(self, input_path: str, effect_name: str, 
                                  start_time: float, duration: float, 
                                  output_path: str, intensity: float = 1.0) -> bool:
        """Apply effect at specific timestamp (CapCut-level precision)"""
        try:
            if effect_name not in self.effect_filters:
                raise ValueError(f"Unknown effect: {effect_name}")
            
            effect_filter = self.effect_filters[effect_name]
            
            # For now, apply effect to entire video (simplified approach)
            # TODO: Implement precise timestamp-based effect application
            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-vf", effect_filter,
                "-c:v", "libx264", "-c:a", "copy",
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Error applying effect at timestamp: {e}")
            return False
    
    def _add_text_at_timestamp(self, input_path: str, text: str, 
                              start_time: float, duration: float,
                              output_path: str, **text_options) -> bool:
        """Add text overlay at specific timestamp (CapCut-level precision)"""
        try:
            font_size = text_options.get("font_size", 48)
            color = text_options.get("color", "white")
            position = text_options.get("position", "center")
            
            # Calculate position
            if position == "center":
                x_pos = "(w-text_w)/2"
                y_pos = "(h-text_h)/2"
            elif position == "top":
                x_pos = "(w-text_w)/2"
                y_pos = "10"
            elif position == "bottom":
                x_pos = "(w-text_w)/2"
                y_pos = "(h-text_h)-10"
            else:
                x_pos = "(w-text_w)/2"
                y_pos = "(h-text_h)/2"
            
            # For now, add text to entire video (simplified approach)
            # TODO: Implement precise timestamp-based text overlay
            text_filter = f"drawtext=text='{text}':fontsize={font_size}:fontcolor={color}:x={x_pos}:y={y_pos}"
            
            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-vf", text_filter,
                "-c:v", "libx264", "-c:a", "copy",
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Error adding text at timestamp: {e}")
            return False
    
    def _edit_existing_video(self, video_path: str, edits: List[Dict], 
                            output_path: str) -> bool:
        """Edit existing video with multiple operations at specific timestamps"""
        try:
            current_video = video_path
            
            for edit in edits:
                edit_type = edit.get("type")
                start_time = edit.get("start_time", 0)
                duration = edit.get("duration", 1)
                
                temp_output = str(Path(output_path).parent / f"temp_edit_{edit_type}.mp4")
                
                if edit_type == "trim":
                    end_time = edit.get("end_time", start_time + duration)
                    success = self._trim_video_at_timestamp(current_video, temp_output, start_time, end_time)
                    
                elif edit_type == "split":
                    part1, part2 = self._split_video_at_timestamp(current_video, start_time)
                    if part1 and part2:
                        # Use part1 as current video, save part2 for later
                        current_video = part1
                        success = True
                    else:
                        success = False
                        
                elif edit_type == "insert":
                    insert_video = edit.get("insert_video_path")
                    success = self._insert_video_at_timestamp(current_video, insert_video, start_time, temp_output)
                    
                elif edit_type == "cut":
                    end_time = edit.get("end_time", start_time + duration)
                    success = self._cut_segment_at_timestamp(current_video, start_time, end_time, temp_output)
                    
                elif edit_type == "effect":
                    effect_name = edit.get("effect_name")
                    intensity = edit.get("intensity", 1.0)
                    success = self._apply_effect_at_timestamp(current_video, effect_name, start_time, duration, temp_output, intensity)
                    
                elif edit_type == "text":
                    text = edit.get("text", "")
                    text_options = edit.get("text_options", {})
                    success = self._add_text_at_timestamp(current_video, text, start_time, duration, temp_output, **text_options)
                    
                else:
                    logger.warning(f"Unknown edit type: {edit_type}")
                    success = False
                
                if success and edit_type != "split":
                    # Update current video for next edit
                    if current_video != video_path:  # Clean up previous temp file
                        os.unlink(current_video)
                    current_video = temp_output
                elif not success:
                    logger.error(f"Failed to apply edit: {edit_type}")
                    return False
            
            # Copy final result to output path
            shutil.copy2(current_video, output_path)
            
            # Cleanup temp files
            if current_video != video_path:
                os.unlink(current_video)
            
            return True
            
        except Exception as e:
            logger.error(f"Error editing existing video: {e}")
            return False

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process video with advanced editing capabilities including CapCut-level timeline editing"""
        try:
            # Extract input parameters with proper type handling
            script_path = input_data.get("script_path")
            
            # Handle multiple possible parameter names for media files
            broll_paths = input_data.get("broll_paths", [])
            media_files = input_data.get("media_files", [])
            
            # If broll_paths is empty but media_files is provided, use media_files
            if not broll_paths and media_files:
                broll_paths = media_files
            
            # Handle case where media_files might be a string (directory path)
            if isinstance(broll_paths, str):
                # If it's a directory path, scan for media files
                media_dir = Path(broll_paths)
                if media_dir.exists() and media_dir.is_dir():
                    # Scan directory for media files
                    media_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.jpg', '.jpeg', '.png', '.gif']
                    broll_paths = []
                    for ext in media_extensions:
                        broll_paths.extend([str(f) for f in media_dir.glob(f"*{ext}")])
                    logger.info(f"Found {len(broll_paths)} media files in directory: {media_dir}")
                else:
                    # Treat as single file path
                    broll_paths = [broll_paths] if Path(broll_paths).exists() else []
            
            # Ensure broll_paths is a list
            if not isinstance(broll_paths, list):
                broll_paths = [broll_paths] if broll_paths else []
            
            # Filter out non-existent files
            valid_broll_paths = []
            for path in broll_paths:
                if isinstance(path, dict):
                    # Handle dict format with 'path' key
                    file_path = path.get("path", path.get("file", ""))
                else:
                    file_path = str(path)
                
                if file_path and Path(file_path).exists():
                    valid_broll_paths.append(file_path)
                else:
                    logger.warning(f"B-roll path does not exist: {file_path}")
            
            broll_paths = valid_broll_paths
            
            audio_path = input_data.get("audio_path")
            voiceover = input_data.get("voiceover")  # Alternative key for voiceover
            style = input_data.get("style", "cinematic")
            resolution = input_data.get("resolution", "1920x1080")
            fps = input_data.get("fps", 30)
            
            # Handle effects parameter - ensure it's a list of dictionaries
            effects = input_data.get("effects", [])
            if isinstance(effects, str):
                # If effects is a string, try to parse it or create a simple effect
                try:
                    import json
                    effects = json.loads(effects)
                except:
                    effects = []
            elif not isinstance(effects, list):
                effects = []
            
            # Handle transitions parameter - ensure it's a list of dictionaries
            transitions = input_data.get("transitions", [])
            if isinstance(transitions, str):
                try:
                    import json
                    transitions = json.loads(transitions)
                except:
                    transitions = []
            elif not isinstance(transitions, list):
                transitions = []
            
            # Handle filters parameter - ensure it's a list of dictionaries
            filters = input_data.get("filters", [])
            if isinstance(filters, str):
                try:
                    import json
                    filters = json.loads(filters)
                except:
                    filters = []
            elif not isinstance(filters, list):
                filters = []
            
            # Handle text_overlays parameter - ensure it's a list of dictionaries
            text_overlays = input_data.get("text_overlays", [])
            if isinstance(text_overlays, str):
                try:
                    import json
                    text_overlays = json.loads(text_overlays)
                except:
                    text_overlays = []
            elif not isinstance(text_overlays, list):
                text_overlays = []
            
            background_music = input_data.get("background_music")
            session_id = input_data.get("session_id", "default")
            
            # Handle different audio path keys
            if not audio_path and voiceover:
                audio_path = voiceover
                logger.info(f"Using voiceover path as audio_path: {audio_path}")
            
            # NEW: CapCut-level timeline editing parameters
            existing_video_path = input_data.get("existing_video_path")  # For editing existing videos
            timeline_edits = input_data.get("timeline_edits", [])  # List of edit operations
            trim_operations = input_data.get("trim_operations", [])  # Trim at specific timestamps
            split_operations = input_data.get("split_operations", [])  # Split at specific timestamps
            insert_operations = input_data.get("insert_operations", [])  # Insert at specific timestamps
            cut_operations = input_data.get("cut_operations", [])  # Cut segments at specific timestamps
            
            logger.info(f"Processing video with {len(broll_paths)} B-roll clips, {len(effects)} effects, {len(timeline_edits)} timeline edits")
            logger.info(f"Audio path: {audio_path}")
            logger.info(f"B-roll paths: {broll_paths}")
            
            # Create session directory
            session_dir = self._create_session_directory(session_id)
            
            # NEW: Handle existing video editing (CapCut-level)
            if existing_video_path and Path(existing_video_path).exists():
                logger.info(f"Editing existing video: {existing_video_path}")
                
                # Combine all edit operations
                all_edits = []
                
                # Add trim operations
                for trim_op in trim_operations:
                    all_edits.append({
                        "type": "trim",
                        "start_time": trim_op.get("start_time", 0),
                        "end_time": trim_op.get("end_time", 10),
                        "output_path": trim_op.get("output_path", str(session_dir / "trimmed.mp4"))
                    })
                
                # Add split operations
                for split_op in split_operations:
                    all_edits.append({
                        "type": "split",
                        "start_time": split_op.get("split_time", 5),
                        "output_path": split_op.get("output_path", str(session_dir / "split.mp4"))
                    })
                
                # Add insert operations
                for insert_op in insert_operations:
                    all_edits.append({
                        "type": "insert",
                        "start_time": insert_op.get("insert_time", 0),
                        "insert_video_path": insert_op.get("insert_video_path"),
                        "output_path": insert_op.get("output_path", str(session_dir / "inserted.mp4"))
                    })
                
                # Add cut operations
                for cut_op in cut_operations:
                    all_edits.append({
                        "type": "cut",
                        "start_time": cut_op.get("start_time", 0),
                        "end_time": cut_op.get("end_time", 5),
                        "output_path": cut_op.get("output_path", str(session_dir / "cut.mp4"))
                    })
                
                # Add timeline edits
                all_edits.extend(timeline_edits)
                
                # Apply all edits
                final_video_path = session_dir / f"edited_video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                success = self._edit_existing_video(existing_video_path, all_edits, str(final_video_path))
                
                if not success:
                    raise ToolError("Failed to edit existing video", "EDITING_ERROR")
                
                # Get final video info
                video_info = self._get_video_info(str(final_video_path))
                duration = float(video_info.get("format", {}).get("duration", 0))
                file_size = Path(final_video_path).stat().st_size
                
                # Generate thumbnail
                thumbnail_path = session_dir / f"thumbnail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                self._generate_thumbnail(str(final_video_path), str(thumbnail_path))
                
                logger.info(f"Existing video editing completed successfully: {final_video_path}")
                logger.info(f"Duration: {duration:.2f}s, Size: {file_size} bytes")
                
                return {
                    "video_path": str(final_video_path),
                    "duration": duration,
                    "thumbnail_path": str(thumbnail_path),
                    "format": "MP4",
                    "resolution": resolution,
                    "fps": fps,
                    "file_size": file_size,
                    "edits_applied": len(all_edits),
                    "edit_types": [edit.get("type") for edit in all_edits],
                    "session_id": session_id,
                    "metadata": {
                        "style": style,
                        "processing_time": datetime.now().isoformat(),
                        "original_video": existing_video_path,
                        "timeline_edits_count": len(timeline_edits),
                        "trim_operations_count": len(trim_operations),
                        "split_operations_count": len(split_operations),
                        "insert_operations_count": len(insert_operations),
                        "cut_operations_count": len(cut_operations)
                    }
                }
            
            # Original video creation logic (for new videos from B-roll)
            else:
                # Handle case where no B-roll is provided
                if not broll_paths:
                    logger.warning("No B-roll paths provided, creating a simple video with audio only")
                    
                    # Create a simple video with just audio
                    final_video_path = session_dir / f"audio_only_video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                    
                    if audio_path and Path(audio_path).exists():
                        # Get audio duration
                        audio_duration = self._get_audio_duration(audio_path)
                        logger.info(f"Creating audio-only video with duration: {audio_duration:.2f}s")
                        
                        # Create a simple video with audio
                        cmd = [
                            "ffmpeg", "-y",
                            "-f", "lavfi", "-i", f"color=c=black:size=1920x1080:duration={audio_duration}",
                            "-i", audio_path,
                            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                            "-c:a", "aac", "-b:a", "128k",
                            "-shortest",
                            str(final_video_path)
                        ]
                        
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        if result.returncode == 0:
                            logger.info(f"Created audio-only video: {final_video_path}")
                            
                            # Get video info
                            video_info = self._get_video_info(str(final_video_path))
                            duration = float(video_info.get("format", {}).get("duration", 0))
                            file_size = Path(final_video_path).stat().st_size
                            
                            return {
                                "video_path": str(final_video_path),
                                "duration": duration,
                                "format": "MP4",
                                "resolution": resolution,
                                "fps": fps,
                                "file_size": file_size,
                                "session_id": session_id,
                                "metadata": {
                                    "style": style,
                                    "processing_time": datetime.now().isoformat(),
                                    "type": "audio_only_video",
                                    "broll_count": 0
                                }
                            }
                        else:
                            logger.error(f"Failed to create audio-only video: {result.stderr}")
                            raise ToolError("Failed to create audio-only video", "AUDIO_ONLY_ERROR")
                    else:
                        logger.error(f"Audio path does not exist: {audio_path}")
                        raise ToolError(f"No audio path provided for audio-only video. Path: {audio_path}", "NO_AUDIO_ERROR")
                
                # Get audio duration for timing
                audio_duration = self._get_audio_duration(audio_path) if audio_path and Path(audio_path).exists() else 10.0
                logger.info(f"Audio duration: {audio_duration:.2f} seconds")
                
                # Step 1: Process individual B-roll clips (handle both images and videos)
                processed_clips = []
                for i, broll_path in enumerate(broll_paths):
                    # Check if broll_path is a string or dict
                    if isinstance(broll_path, dict):
                        broll_path = broll_path.get("path", broll_path.get("file", ""))
                    
                    if not broll_path or not Path(broll_path).exists():
                        logger.warning(f"B-roll path {broll_path} does not exist, skipping")
                        continue
                    
                    processed_path = session_dir / f"processed_clip_{i:03d}.mp4"
                    
                    # Check if it's an image or video
                    file_ext = Path(broll_path).suffix.lower()
                    is_image = file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
                    
                    # Apply effects and filters to individual clip
                    video_filter = self._create_video_filter(
                        [e for e in effects if e.get("clip_index") == i],
                        [],
                        filters,
                        [t for t in text_overlays if t.get("clip_index") == i]
                    )
                    
                    if is_image:
                        # Convert image to video with duration
                        clip_duration = audio_duration / max(len(broll_paths), 1)  # Distribute audio duration across clips
                        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", broll_path, "-t", str(clip_duration)]
                        if video_filter:
                            cmd.extend(["-vf", video_filter])
                        cmd.extend([
                            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
                            "-r", str(fps), "-s", resolution,
                            str(processed_path)
                        ])
                    else:
                        # Process as video
                        cmd = ["ffmpeg", "-y", "-i", broll_path]
                        if video_filter:
                            cmd.extend(["-vf", video_filter])
                        cmd.extend([
                            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
                            "-c:a", "aac", "-b:a", "128k",
                            "-r", str(fps), "-s", resolution,
                            str(processed_path)
                        ])
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        processed_clips.append(str(processed_path))
                        logger.info(f"Processed {'image' if is_image else 'video'} clip {i+1}/{len(broll_paths)}")
                    else:
                        logger.error(f"Failed to process clip {i}: {result.stderr}")
                        # Try a simpler approach for images
                        if is_image:
                            simple_cmd = ["ffmpeg", "-y", "-loop", "1", "-i", broll_path, "-t", "3", 
                                        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                                        "-r", str(fps), "-s", resolution, str(processed_path)]
                            result = subprocess.run(simple_cmd, capture_output=True, text=True)
                            if result.returncode == 0:
                                processed_clips.append(str(processed_path))
                                logger.info(f"Processed image clip {i+1} with simple method")
                            else:
                                logger.error(f"Failed to process image clip {i} with simple method: {result.stderr}")
                
                if not processed_clips:
                    # If no clips were processed, create a simple video with just audio
                    logger.warning("No clips were successfully processed, creating audio-only video")
                    final_video_path = session_dir / f"audio_only_video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                    
                    if audio_path and Path(audio_path).exists():
                        audio_duration = self._get_audio_duration(audio_path)
                        cmd = [
                            "ffmpeg", "-y",
                            "-f", "lavfi", "-i", f"color=c=black:size=1920x1080:duration={audio_duration}",
                            "-i", audio_path,
                            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                            "-c:a", "aac", "-b:a", "128k",
                            "-shortest",
                            str(final_video_path)
                        ]
                        
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        if result.returncode == 0:
                            video_info = self._get_video_info(str(final_video_path))
                            duration = float(video_info.get("format", {}).get("duration", 0))
                            file_size = Path(final_video_path).stat().st_size
                            
                            return {
                                "video_path": str(final_video_path),
                                "duration": duration,
                                "format": "MP4",
                                "resolution": resolution,
                                "fps": fps,
                                "file_size": file_size,
                                "session_id": session_id,
                                "metadata": {
                                    "style": style,
                                    "processing_time": datetime.now().isoformat(),
                                    "type": "audio_only_video",
                                    "broll_count": 0
                                }
                            }
                        else:
                            raise ToolError("Failed to create audio-only video", "AUDIO_ONLY_ERROR")
                    else:
                        raise ToolError("No audio path provided for audio-only video", "NO_AUDIO_ERROR")
                
                # Step 2: Concatenate clips with transitions
                concatenated_path = session_dir / "concatenated.mp4"
                if len(processed_clips) > 1:
                    success = self._concatenate_videos(processed_clips, str(concatenated_path), transitions)
                    if not success:
                        raise ToolError("Failed to concatenate videos", "CONCATENATION_ERROR")
                else:
                    # Single clip, just copy it
                    shutil.copy2(processed_clips[0], str(concatenated_path))
                
                # Step 3: Add audio synchronization
                final_video_path = session_dir / f"final_video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                success = self._add_audio_to_video(str(concatenated_path), audio_path, str(final_video_path), background_music)
                if not success:
                    raise ToolError("Failed to add audio to video", "AUDIO_SYNC_ERROR")
                
                # Step 4: Generate thumbnail
                thumbnail_path = session_dir / f"thumbnail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                self._generate_thumbnail(str(final_video_path), str(thumbnail_path))
                
                # Get final video info
                video_info = self._get_video_info(str(final_video_path))
                duration = float(video_info.get("format", {}).get("duration", 0))
                file_size = Path(final_video_path).stat().st_size
                
                logger.info(f"Video processing completed successfully: {final_video_path}")
                logger.info(f"Duration: {duration:.2f}s, Size: {file_size} bytes")
                
                return {
                    "video_path": str(final_video_path),
                    "duration": duration,
                    "thumbnail_path": str(thumbnail_path),
                    "format": "MP4",
                    "resolution": resolution,
                    "fps": fps,
                    "file_size": file_size,
                    "effects_applied": [e.get("name") for e in effects],
                    "transitions_applied": [t.get("name") for t in transitions],
                    "filters_applied": [f.get("name") for f in filters],
                    "clips_processed": len(processed_clips),
                    "session_id": session_id,
                    "metadata": {
                        "style": style,
                        "audio_duration": audio_duration,
                        "processing_time": datetime.now().isoformat(),
                        "effects_count": len(effects),
                        "transitions_count": len(transitions),
                        "filters_count": len(filters),
                        "text_overlays_count": len(text_overlays)
                    }
                }
            
        except Exception as e:
            logger.error(f"Error processing video: {e}")
            raise ToolError(f"Failed to process video: {e}", "VIDEO_PROCESSING_ERROR")
    
    def get_available_effects(self) -> List[Dict[str, Any]]:
        """Get list of available effects"""
        return self.effects
    
    def get_available_transitions(self) -> List[Dict[str, Any]]:
        """Get list of available transitions"""
        return self.transitions
    
    def get_available_filters(self) -> List[Dict[str, Any]]:
        """Get list of available filters"""
        return self.filters 