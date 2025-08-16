"""
Configuration settings for Sclip FastAPI Backend
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = "Sclip Backend"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    
    # CORS
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://localhost:1420",
        "http://127.0.0.1:1420",
        "tauri://localhost"
    ]
    
    # Database
    database_url: str = "sqlite:///./sclip.db"
    
    # File storage
    upload_dir: str = "uploads"
    temp_dir: str = "temp"
    sessions_dir: str = "sessions"
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    
    # Session management
    session_timeout: int = 3600  # 1 hour
    max_sessions_per_user: int = 10
    
    # API Keys (from environment variables) - match .env file names
    google_custom_search_api_key: Optional[str] = None
    google_custom_search_engine_id: Optional[str] = None
    pexels_api_key: Optional[str] = None
    runware_api_key: Optional[str] = None
    youtube_data_api_key: Optional[str] = None
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-pro"
    
    # Download settings (from .env)
    max_download_concurrency: int = 5
    download_timeout: int = 30
    
    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 3600  # 1 hour
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/sclip.log"
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Media processing
    max_video_duration: int = 600  # 10 minutes
    supported_video_formats: List[str] = ["mp4", "avi", "mov", "mkv"]
    supported_audio_formats: List[str] = ["mp3", "wav", "aac", "ogg"]
    supported_image_formats: List[str] = ["jpg", "jpeg", "png", "gif", "webp"]
    
    # Tool settings
    script_writer_timeout: int = 300  # 5 minutes
    broll_finder_timeout: int = 600   # 10 minutes
    voiceover_generator_timeout: int = 300  # 5 minutes
    video_processor_timeout: int = 1800  # 30 minutes
    
    # WebSocket
    websocket_ping_interval: int = 20
    websocket_ping_timeout: int = 20
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env

# Create settings instance
settings = Settings()

# Ensure directories exist
def ensure_directories():
    """Create necessary directories if they don't exist"""
    directories = [
        settings.upload_dir,
        settings.temp_dir,
        settings.sessions_dir,
        "logs",
        "temp/scripts",
        "temp/voiceovers",
        "temp/videos"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

# Initialize directories
ensure_directories() 