"""
User Preferences Model for Sclip
Comprehensive user preferences and context management
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum

class ApprovalMode(Enum):
    """User approval mode enumeration"""
    AUTO_APPROVE = "auto_approve"
    MAJOR_STEPS_ONLY = "major_steps_only"
    EVERY_STEP = "every_step"

class ConfirmationFrequency(Enum):
    """Confirmation frequency enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class VideoStyle(Enum):
    """Video style enumeration"""
    CINEMATIC = "cinematic"
    DOCUMENTARY = "documentary"
    SOCIAL_MEDIA = "social_media"
    NEWS = "news"
    EDUCATIONAL = "educational"
    ENTERTAINMENT = "entertainment"

class VoiceType(Enum):
    """Voice type enumeration"""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    ENERGETIC = "energetic"
    CALM = "calm"
    AUTHORITATIVE = "authoritative"
    FRIENDLY = "friendly"

class EditingPace(Enum):
    """Editing pace enumeration"""
    SLOW = "slow"
    MEDIUM = "medium"
    FAST = "fast"

class InteractionLevel(Enum):
    """User interaction level enumeration"""
    HANDS_OFF = "hands_off"
    GUIDED = "guided"
    HANDS_ON = "hands_on"

class QualitySetting(Enum):
    """Quality setting enumeration"""
    DRAFT = "draft"
    STANDARD = "standard"
    HIGH = "high"

class NotificationPreference(Enum):
    """Notification preference enumeration"""
    DESKTOP = "desktop"
    EMAIL = "email"
    SILENT = "silent"

class StylePreferences(BaseModel):
    """User style preferences for video creation"""
    video_style: VideoStyle = VideoStyle.CINEMATIC
    voice_type: VoiceType = VoiceType.PROFESSIONAL
    editing_pace: EditingPace = EditingPace.MEDIUM
    content_themes: List[str] = Field(default_factory=list)
    color_scheme: Optional[str] = None
    music_preference: Optional[str] = None
    transition_style: Optional[str] = None
    subtitle_preference: bool = True
    background_music: bool = True

class UserPreferences(BaseModel):
    """
    Comprehensive user preferences for Sclip
    Controls orchestrator behavior and video creation style
    """
    # Process Control
    approval_mode: ApprovalMode = ApprovalMode.AUTO_APPROVE
    confirmation_frequency: ConfirmationFrequency = ConfirmationFrequency.LOW
    interaction_level: InteractionLevel = InteractionLevel.HANDS_OFF
    
    # Quality Settings
    quality_setting: QualitySetting = QualitySetting.STANDARD
    
    # Style Preferences
    style_preferences: StylePreferences = Field(default_factory=StylePreferences)
    
    # Notification Preferences
    notification_preferences: NotificationPreference = NotificationPreference.DESKTOP
    
    # Advanced Settings
    auto_save_interval: int = 300  # seconds
    max_retry_attempts: int = 3
    session_timeout: int = 3600  # seconds
    enable_analytics: bool = True
    enable_feedback_collection: bool = True
    
    # Content Preferences
    preferred_topics: List[str] = Field(default_factory=list)
    avoided_topics: List[str] = Field(default_factory=list)
    content_language: str = "en"
    subtitle_language: Optional[str] = None
    
    # Performance Preferences
    enable_caching: bool = True
    enable_parallel_processing: bool = True
    max_concurrent_tools: int = 2
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert preferences to dictionary"""
        return self.dict()
    
    def update_from_dict(self, updates: Dict[str, Any]):
        """Update preferences from dictionary"""
        for key, value in updates.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def get_approval_required(self, step_type: str) -> bool:
        """Determine if approval is required for a step type"""
        if self.approval_mode == ApprovalMode.AUTO_APPROVE:
            return False
        elif self.approval_mode == ApprovalMode.MAJOR_STEPS_ONLY:
            major_steps = ["script_generation", "video_assembly", "final_output"]
            return step_type in major_steps
        else:  # EVERY_STEP
            return True
    
    def get_retry_attempts(self) -> int:
        """Get maximum retry attempts based on quality setting"""
        if self.quality_setting == QualitySetting.DRAFT:
            return 1
        elif self.quality_setting == QualitySetting.STANDARD:
            return self.max_retry_attempts
        else:  # HIGH
            return self.max_retry_attempts + 1

class UserContext(BaseModel):
    """
    User context for adaptive behavior
    Tracks user behavior patterns and preferences
    """
    user_id: str
    session_count: int = 0
    total_videos_created: int = 0
    average_session_duration: float = 0.0
    preferred_video_length: Optional[int] = None  # in seconds
    most_used_topics: List[str] = Field(default_factory=list)
    successful_patterns: List[Dict[str, Any]] = Field(default_factory=list)
    intervention_points: List[Dict[str, Any]] = Field(default_factory=list)
    satisfaction_ratings: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def add_session(self, session_duration: float, topics: List[str] = None):
        """Add a new session to context"""
        self.session_count += 1
        self.total_videos_created += 1
        
        # Update average session duration
        if self.session_count == 1:
            self.average_session_duration = session_duration
        else:
            total_duration = self.average_session_duration * (self.session_count - 1) + session_duration
            self.average_session_duration = total_duration / self.session_count
        
        # Update topics
        if topics:
            for topic in topics:
                if topic not in self.most_used_topics:
                    self.most_used_topics.append(topic)
        
        self.updated_at = datetime.now()
    
    def add_successful_pattern(self, pattern: Dict[str, Any]):
        """Add a successful pattern to context"""
        self.successful_patterns.append({
            **pattern,
            "timestamp": datetime.now().isoformat()
        })
        self.updated_at = datetime.now()
    
    def add_intervention_point(self, step: str, reason: str, user_action: str):
        """Add an intervention point to context"""
        self.intervention_points.append({
            "step": step,
            "reason": reason,
            "user_action": user_action,
            "timestamp": datetime.now().isoformat()
        })
        self.updated_at = datetime.now()
    
    def add_satisfaction_rating(self, session_id: str, rating: int, feedback: str = None):
        """Add a satisfaction rating to context"""
        self.satisfaction_ratings.append({
            "session_id": session_id,
            "rating": rating,
            "feedback": feedback,
            "timestamp": datetime.now().isoformat()
        })
        self.updated_at = datetime.now()
    
    def get_average_satisfaction(self) -> float:
        """Get average satisfaction rating"""
        if not self.satisfaction_ratings:
            return 0.0
        
        total_rating = sum(rating["rating"] for rating in self.satisfaction_ratings)
        return total_rating / len(self.satisfaction_ratings)
    
    def get_intervention_frequency(self) -> float:
        """Get intervention frequency (interventions per session)"""
        if self.session_count == 0:
            return 0.0
        
        return len(self.intervention_points) / self.session_count
    
    def get_preferred_topics(self, limit: int = 5) -> List[str]:
        """Get most used topics"""
        return self.most_used_topics[:limit]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary"""
        return {
            "user_id": self.user_id,
            "session_count": self.session_count,
            "total_videos_created": self.total_videos_created,
            "average_session_duration": self.average_session_duration,
            "preferred_video_length": self.preferred_video_length,
            "most_used_topics": self.most_used_topics,
            "average_satisfaction": self.get_average_satisfaction(),
            "intervention_frequency": self.get_intervention_frequency(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        } 