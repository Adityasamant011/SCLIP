"""
User model for Sclip
Manages user data, preferences, and session history
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum

class UserRole(Enum):
    """User role enumeration"""
    USER = "user"
    ADMIN = "admin"
    PREMIUM = "premium"

class UserPreferences(BaseModel):
    """User preferences for video creation"""
    approval_mode: str = "auto_approve"  # auto_approve, major_steps_only, every_step
    confirmation_frequency: str = "low"  # low, medium, high
    style_preferences: Dict[str, Any] = {
        "video_style": "cinematic",
        "voice_type": "professional",
        "editing_pace": "medium"
    }
    interaction_level: str = "hands_off"  # hands_off, guided, hands_on
    quality_setting: str = "standard"  # draft, standard, high
    notification_preferences: str = "desktop"  # desktop, email, silent

class User(BaseModel):
    """
    User model for managing user data and preferences
    """
    user_id: str
    username: Optional[str] = None
    email: Optional[str] = None
    role: UserRole = UserRole.USER
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    session_history: List[str] = []  # List of session IDs
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    is_active: bool = True
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def add_session(self, session_id: str):
        """Add a session to user's history"""
        if session_id not in self.session_history:
            self.session_history.append(session_id)
            self.updated_at = datetime.now()
    
    def remove_session(self, session_id: str):
        """Remove a session from user's history"""
        if session_id in self.session_history:
            self.session_history.remove(session_id)
            self.updated_at = datetime.now()
    
    def update_preferences(self, preferences: Dict[str, Any]):
        """Update user preferences"""
        for key, value in preferences.items():
            if hasattr(self.preferences, key):
                setattr(self.preferences, key, value)
        self.updated_at = datetime.now()
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.now()
        self.updated_at = datetime.now()
    
    def get_user_summary(self) -> Dict[str, Any]:
        """Get a summary of the user"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role.value,
            "session_count": len(self.session_history),
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "is_active": self.is_active
        } 