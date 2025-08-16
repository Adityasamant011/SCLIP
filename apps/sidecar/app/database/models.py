"""
SQLAlchemy database models for Sclip
Defines the database schema for sessions, users, and related data
"""
from sqlalchemy import Column, String, DateTime, Integer, Boolean, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database.connection import Base

class DBSession(Base):
    """Database model for sessions"""
    __tablename__ = "sessions"
    
    session_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=True)  # Add user_id field
    user_prompt = Column(Text, nullable=False)
    current_step = Column(String, nullable=True)
    status = Column(String, nullable=False, default="awaiting_prompt")
    user_context = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    workflow_steps = relationship("DBWorkflowStep", back_populates="session", cascade="all, delete-orphan")
    tool_outputs = relationship("DBToolOutput", back_populates="session", cascade="all, delete-orphan")
    user_approvals = relationship("DBUserApproval", back_populates="session", cascade="all, delete-orphan")

class DBWorkflowStep(Base):
    """Database model for workflow steps"""
    __tablename__ = "workflow_steps"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.session_id"), nullable=False)
    step_id = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    tool = Column(String, nullable=False)
    args = Column(JSON, nullable=True)
    status = Column(String, nullable=False, default="pending")
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    session = relationship("DBSession", back_populates="workflow_steps")
    output = relationship("DBToolOutput", back_populates="workflow_step", uselist=False)
    user_approval = relationship("DBUserApproval", back_populates="workflow_step", uselist=False)

class DBToolOutput(Base):
    """Database model for tool outputs"""
    __tablename__ = "tool_outputs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.session_id"), nullable=False)
    step_id = Column(String, ForeignKey("workflow_steps.step_id"), nullable=False)
    tool = Column(String, nullable=False)
    success = Column(Boolean, nullable=False)
    output = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    execution_time = Column(Integer, nullable=False)  # in milliseconds
    timestamp = Column(DateTime, default=datetime.now)
    verification_passed = Column(Boolean, default=False)
    
    # Relationships
    session = relationship("DBSession", back_populates="tool_outputs")
    workflow_step = relationship("DBWorkflowStep", back_populates="output")

class DBUserApproval(Base):
    """Database model for user approvals"""
    __tablename__ = "user_approvals"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.session_id"), nullable=False)
    step_id = Column(String, ForeignKey("workflow_steps.step_id"), nullable=False)
    approved = Column(Boolean, nullable=False)
    feedback = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.now)
    user_id = Column(String, nullable=True)
    
    # Relationships
    session = relationship("DBSession", back_populates="user_approvals")
    workflow_step = relationship("DBWorkflowStep", back_populates="user_approval")

class DBUser(Base):
    """Database model for users"""
    __tablename__ = "users"
    
    user_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, nullable=True)
    email = Column(String, nullable=True)
    role = Column(String, nullable=False, default="user")
    preferences = Column(JSON, nullable=True)
    context = Column(JSON, nullable=True)  # Store user context as JSON
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

class DBSessionHistory(Base):
    """Database model for session history tracking"""
    __tablename__ = "session_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.session_id"), nullable=False)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=True)
    action = Column(String, nullable=False)  # created, started, completed, failed, etc.
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.now)
    
    # Relationships
    session = relationship("DBSession")
    user = relationship("DBUser") 