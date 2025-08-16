"""
Context Manager for Sclip
Handles user context learning, preference inference, and adaptive behavior
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
import re

from app.models.preferences import UserPreferences, UserContext, ApprovalMode, VideoStyle, VoiceType
from app.models.session import Session, SessionStatus
from app.database.connection import get_db
from app.database.models import DBUser, DBSession as DBSessionModel
from app.utils.logger import get_logger

logger = get_logger(__name__)

def get_enum_value(enum_obj):
    """Safely get enum value, handling both enum objects and strings"""
    if hasattr(enum_obj, 'value'):
        return enum_obj.value
    return str(enum_obj)

class ContextManager:
    """
    Manages user context and adaptive behavior
    Learns from user interactions and adjusts orchestrator behavior
    """
    
    def __init__(self):
        self.user_contexts: Dict[str, UserContext] = {}
        self.user_preferences: Dict[str, UserPreferences] = {}
        self.pattern_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.learning_enabled: bool = True
        
        logger.info("Context manager initialized")
    
    async def get_user_preferences(self, user_id: str) -> UserPreferences:
        """Get user preferences, creating defaults if not exists"""
        if user_id not in self.user_preferences:
            # Try to load from database
            prefs = await self._load_preferences_from_db(user_id)
            if prefs:
                self.user_preferences[user_id] = prefs
            else:
                # Create default preferences
                self.user_preferences[user_id] = UserPreferences()
                await self._save_preferences_to_db(user_id, self.user_preferences[user_id])
        
        return self.user_preferences[user_id]
    
    async def update_user_preferences(self, user_id: str, updates: Dict[str, Any]):
        """Update user preferences"""
        prefs = await self.get_user_preferences(user_id)
        prefs.update_from_dict(updates)
        
        # Save to database
        await self._save_preferences_to_db(user_id, prefs)
        
        logger.info("User preferences updated", user_id=user_id, updates=updates)
    
    async def get_user_context(self, user_id: str) -> UserContext:
        """Get user context, creating if not exists"""
        if user_id not in self.user_contexts:
            # Try to load from database
            context = await self._load_context_from_db(user_id)
            if context:
                self.user_contexts[user_id] = context
            else:
                # Create new context
                self.user_contexts[user_id] = UserContext(user_id=user_id)
                await self._save_context_to_db(user_id, self.user_contexts[user_id])
        
        return self.user_contexts[user_id]
    
    async def update_user_context(self, user_id: str, context: UserContext):
        """Update user context"""
        self.user_contexts[user_id] = context
        await self._save_context_to_db(user_id, context)
    
    async def learn_from_session(self, session: Session):
        """Learn from a completed session"""
        if not self.learning_enabled:
            return
        
        user_id = session.user_context.get("user_id", "anonymous")
        if not user_id or user_id == "anonymous":
            return
        
        try:
            # Get user context
            context = await self.get_user_context(user_id)
            
            # Calculate session duration
            if session.completed_at and session.created_at:
                duration = (session.completed_at - session.created_at).total_seconds()
            else:
                duration = 0.0
            
            # Extract topics from user prompt
            topics = self._extract_topics(session.user_prompt)
            
            # Update context with session data
            context.add_session(duration, topics)
            
            # Analyze successful patterns
            if session.status == SessionStatus.COMPLETED:
                pattern = self._extract_successful_pattern(session)
                if pattern:
                    context.add_successful_pattern(pattern)
            
            # Analyze intervention points
            for approval in session.user_approvals:
                if not approval.approved:
                    context.add_intervention_point(
                        step=approval.step_id,
                        reason="User rejection",
                        user_action="rejected"
                    )
            
            # Save updated context
            await self.update_user_context(user_id, context)
            
            # Infer preferences from behavior
            await self._infer_preferences_from_behavior(user_id, session)
            
            logger.info("Learned from session", user_id=user_id, session_id=session.session_id)
            
        except Exception as e:
            logger.error("Failed to learn from session", error=str(e))
    
    async def get_adaptive_behavior(self, user_id: str, session_type: str = "video_creation") -> Dict[str, Any]:
        """Get adaptive behavior settings for a user"""
        prefs = await self.get_user_preferences(user_id)
        context = await self.get_user_context(user_id)
        
        # Base behavior from preferences
        behavior = {
            "approval_required": prefs.get_approval_required(session_type),
            "retry_attempts": prefs.get_retry_attempts(),
            "interaction_level": get_enum_value(prefs.interaction_level),
            "quality_setting": get_enum_value(prefs.quality_setting),
            "style_preferences": prefs.style_preferences.dict() if hasattr(prefs.style_preferences, 'dict') else prefs.style_preferences
        }
        
        # Adapt based on user context
        if context.session_count > 5:
            # Experienced user - reduce confirmations
            if context.get_intervention_frequency() < 0.2:  # Less than 20% interventions
                behavior["approval_required"] = False
                behavior["interaction_level"] = "hands_off"
        
        avg_satisfaction = context.get_average_satisfaction()
        if avg_satisfaction > 4.0:
            # High satisfaction - maintain current settings
            behavior["confidence_level"] = "high"
        elif avg_satisfaction < 2.5:
            # Low satisfaction - increase confirmations
            behavior["approval_required"] = True
            behavior["interaction_level"] = "guided"
            behavior["confidence_level"] = "low"
        
        # Adapt based on preferred topics
        if context.most_used_topics:
            behavior["suggested_topics"] = context.get_preferred_topics()
        
        return behavior
    
    async def get_context_aware_prompt(self, user_id: str, base_prompt: str) -> str:
        """Generate a context-aware prompt for the orchestrator"""
        prefs = await self.get_user_preferences(user_id)
        context = await self.get_user_context(user_id)
        
        # Build context information
        context_info = []
        
        # User preferences
        if hasattr(prefs.style_preferences, 'video_style'):
            context_info.append(f"User prefers {get_enum_value(prefs.style_preferences.video_style)} style videos")
            context_info.append(f"User prefers {get_enum_value(prefs.style_preferences.voice_type)} voice")
        else:
            context_info.append("User has default style preferences")
        
        context_info.append(f"User interaction level: {get_enum_value(prefs.interaction_level)}")
        
        # User history
        if context.session_count > 0:
            context_info.append(f"User has created {context.total_videos_created} videos")
            context_info.append(f"Average session duration: {context.average_session_duration:.1f} seconds")
        
        # Preferred topics
        if context.most_used_topics:
            topics_str = ", ".join(context.get_preferred_topics(3))
            context_info.append(f"User frequently creates videos about: {topics_str}")
        
        # Satisfaction level
        if context.satisfaction_ratings:
            avg_satisfaction = context.get_average_satisfaction()
            context_info.append(f"User satisfaction level: {avg_satisfaction:.1f}/5")
        
        # Combine into enhanced prompt
        enhanced_prompt = f"{base_prompt}\n\nUser Context: {'; '.join(context_info)}"
        
        return enhanced_prompt
    
    async def _infer_preferences_from_behavior(self, user_id: str, session: Session):
        """Infer user preferences from session behavior"""
        prefs = await self.get_user_preferences(user_id)
        
        # Analyze approval patterns
        total_approvals = len(session.user_approvals)
        approved_count = sum(1 for approval in session.user_approvals if approval.approved)
        
        if total_approvals > 0:
            approval_rate = approved_count / total_approvals
            
            # Adjust approval mode based on approval rate
            if approval_rate > 0.9:  # High approval rate
                if prefs.approval_mode != ApprovalMode.AUTO_APPROVE:
                    prefs.approval_mode = ApprovalMode.AUTO_APPROVE
                    logger.info("Inferred auto-approve preference", user_id=user_id)
            elif approval_rate < 0.5:  # Low approval rate
                if prefs.approval_mode != ApprovalMode.EVERY_STEP:
                    prefs.approval_mode = ApprovalMode.EVERY_STEP
                    logger.info("Inferred every-step approval preference", user_id=user_id)
        
        # Analyze intervention frequency
        context = await self.get_user_context(user_id)
        intervention_freq = context.get_intervention_frequency()
        
        if intervention_freq > 0.5:  # High intervention rate
            prefs.interaction_level = "hands_on"
        elif intervention_freq < 0.1:  # Low intervention rate
            prefs.interaction_level = "hands_off"
        
        # Save updated preferences
        await self._save_preferences_to_db(user_id, prefs)
    
    def _extract_topics(self, prompt: str) -> List[str]:
        """Extract topics from user prompt"""
        # Simple topic extraction - can be enhanced with NLP
        topics = []
        
        # Common video topics
        common_topics = [
            "sports", "football", "soccer", "basketball", "tennis", "golf",
            "music", "concert", "performance", "album", "song",
            "movie", "film", "trailer", "review", "cinema",
            "news", "politics", "business", "technology", "science",
            "education", "tutorial", "how-to", "lesson", "course",
            "travel", "vacation", "destination", "tourism", "adventure",
            "food", "cooking", "recipe", "restaurant", "cuisine",
            "fashion", "style", "clothing", "beauty", "makeup",
            "gaming", "game", "esports", "streaming", "playthrough"
        ]
        
        prompt_lower = prompt.lower()
        for topic in common_topics:
            if topic in prompt_lower:
                topics.append(topic)
        
        return topics
    
    def _extract_successful_pattern(self, session: Session) -> Optional[Dict[str, Any]]:
        """Extract successful pattern from session"""
        if not session.workflow_steps:
            return None
        
        # Analyze successful workflow
        pattern = {
            "workflow_steps": len(session.workflow_steps),
            "tools_used": list(set(step.tool for step in session.workflow_steps)),
            "total_duration": 0.0,
            "successful_steps": 0
        }
        
        # Calculate total execution time
        for output in session.tool_outputs.values():
            if output.success:
                pattern["total_duration"] += output.execution_time
                pattern["successful_steps"] += 1
        
        return pattern
    
    async def _save_preferences_to_db(self, user_id: str, preferences: UserPreferences):
        """Save user preferences to database"""
        try:
            db = next(get_db())
            db_user = db.query(DBUser).filter(DBUser.user_id == user_id).first()
            
            # Convert preferences to JSON-serializable format
            prefs_dict = preferences.to_dict()
            
            # Convert enum values to strings for JSON serialization
            if 'approval_mode' in prefs_dict:
                prefs_dict['approval_mode'] = get_enum_value(prefs_dict['approval_mode'])
            if 'confirmation_frequency' in prefs_dict:
                prefs_dict['confirmation_frequency'] = get_enum_value(prefs_dict['confirmation_frequency'])
            if 'interaction_level' in prefs_dict:
                prefs_dict['interaction_level'] = get_enum_value(prefs_dict['interaction_level'])
            if 'quality_setting' in prefs_dict:
                prefs_dict['quality_setting'] = get_enum_value(prefs_dict['quality_setting'])
            if 'notification_preferences' in prefs_dict:
                prefs_dict['notification_preferences'] = get_enum_value(prefs_dict['notification_preferences'])
            
            # Handle style preferences
            if 'style_preferences' in prefs_dict:
                style_prefs = prefs_dict['style_preferences']
                if 'video_style' in style_prefs:
                    style_prefs['video_style'] = get_enum_value(style_prefs['video_style'])
                if 'voice_type' in style_prefs:
                    style_prefs['voice_type'] = get_enum_value(style_prefs['voice_type'])
                if 'editing_pace' in style_prefs:
                    style_prefs['editing_pace'] = get_enum_value(style_prefs['editing_pace'])
            
            if db_user:
                db_user.preferences = prefs_dict
                db_user.updated_at = datetime.now()
            else:
                # Create new user
                db_user = DBUser(
                    user_id=user_id,
                    preferences=prefs_dict,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(db_user)
            
            db.commit()
            logger.info(f"User preferences saved to database for {user_id}")
            
        except Exception as e:
            logger.error("Failed to save preferences to database", error=str(e))
            if 'db' in locals():
                db.rollback()
        finally:
            if 'db' in locals():
                db.close()
    
    async def _load_preferences_from_db(self, user_id: str) -> Optional[UserPreferences]:
        """Load user preferences from database"""
        try:
            db = next(get_db())
            db_user = db.query(DBUser).filter(DBUser.user_id == user_id).first()
            
            if db_user and db_user.preferences:
                return UserPreferences(**db_user.preferences)
            
            return None
            
        except Exception as e:
            logger.error("Failed to load preferences from database", error=str(e))
            return None
        finally:
            if 'db' in locals():
                db.close()
    
    async def _load_context_from_db(self, user_id: str) -> Optional[UserContext]:
        """Load user context from database"""
        try:
            db = next(get_db())
            db_user = db.query(DBUser).filter(DBUser.user_id == user_id).first()
            
            if db_user and db_user.context:
                return UserContext(**db_user.context)
            
            return None
            
        except Exception as e:
            logger.error("Failed to load context from database", error=str(e))
            return None
        finally:
            if 'db' in locals():
                db.close()
    
    async def _save_context_to_db(self, user_id: str, context: UserContext):
        """Save user context to database"""
        try:
            db = next(get_db())
            db_user = db.query(DBUser).filter(DBUser.user_id == user_id).first()
            
            # Convert context to JSON-serializable format
            context_dict = context.to_dict()
            
            # Convert datetime objects to ISO strings for JSON serialization
            if 'satisfaction_ratings' in context_dict:
                for rating in context_dict['satisfaction_ratings']:
                    if 'timestamp' in rating:
                        rating['timestamp'] = rating['timestamp'].isoformat()
            
            if 'intervention_points' in context_dict:
                for point in context_dict['intervention_points']:
                    if 'timestamp' in point:
                        point['timestamp'] = point['timestamp'].isoformat()
            
            if db_user:
                db_user.context = context_dict
                db_user.updated_at = datetime.now()
            else:
                # Create new user with context
                db_user = DBUser(
                    user_id=user_id,
                    context=context_dict,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(db_user)
            
            db.commit()
            logger.info(f"User context saved to database for {user_id}")
            
        except Exception as e:
            logger.error("Failed to save context to database", error=str(e))
            if 'db' in locals():
                db.rollback()
        finally:
            if 'db' in locals():
                db.close()

# Global context manager instance
context_manager = ContextManager() 