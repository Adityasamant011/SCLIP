"""
Session Manager for Sclip
Manages in-memory session state with database persistence
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from sqlalchemy.orm import Session as DBSession

from apps.sidecar.app.models.session import Session, SessionStatus, WorkflowStep, ToolOutput, UserApproval
from apps.sidecar.app.database.connection import get_db, create_tables
from apps.sidecar.app.database.models import DBSession as DBSessionModel, DBWorkflowStep, DBToolOutput, DBUserApproval
from apps.sidecar.app.utils.logger import get_logger

logger = get_logger(__name__)

class SessionManager:
    """
    Manages session state in memory with database persistence
    Handles session creation, updates, cleanup, and recovery
    """
    
    def __init__(self):
        self.active_sessions: Dict[str, Session] = {}
        self.session_timeouts: Dict[str, datetime] = {}
        self.cleanup_task: Optional[asyncio.Task] = None
        self.max_sessions = 100  # Maximum active sessions in memory
        
        logger.info("Session manager initialized")
    
    async def start(self):
        """Start the session manager"""
        # Create database tables if they don't exist
        create_tables()
        
        # Start cleanup task
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("Session manager started")
    
    async def stop(self):
        """Stop the session manager"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Persist all active sessions
        await self._persist_all_sessions()
        
        logger.info("Session manager stopped")
    
    async def create_session(self, user_prompt: str, user_context: Dict[str, Any] = None) -> Session:
        """Create a new session"""
        session_id = str(uuid.uuid4())
        
        # Create session object
        session = Session(
            session_id=session_id,
            user_prompt=user_prompt,
            user_context=user_context or {},
            status=SessionStatus.AWAITING_PROMPT
        )
        
        # Add to active sessions
        self.active_sessions[session_id] = session
        self.session_timeouts[session_id] = datetime.now() + timedelta(hours=1)
        
        # Persist to database
        await self._persist_session(session)
        
        logger.info("Session created", session_id=session_id, user_prompt=user_prompt)
        return session
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID"""
        # Check in-memory first
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]
        
        # Load from database
        session = await self._load_session_from_db(session_id)
        if session:
            self.active_sessions[session_id] = session
            self.session_timeouts[session_id] = datetime.now() + timedelta(hours=1)
        
        return session
    
    async def update_session(self, session: Session):
        """Update a session"""
        session.updated_at = datetime.now()
        
        # Update in-memory
        self.active_sessions[session.session_id] = session
        self.session_timeouts[session.session_id] = datetime.now() + timedelta(hours=1)
        
        # Persist to database
        await self._persist_session(session)
        
        logger.debug("Session updated", session_id=session.session_id)
    
    async def delete_session(self, session_id: str):
        """Delete a session"""
        # Remove from memory
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        if session_id in self.session_timeouts:
            del self.session_timeouts[session_id]
        
        # Remove from database
        await self._delete_session_from_db(session_id)
        
        logger.info("Session deleted", session_id=session_id)
    
    async def list_sessions(self, user_id: Optional[str] = None, limit: int = 50) -> List[Session]:
        """List sessions with optional filtering"""
        sessions = list(self.active_sessions.values())
        
        # Filter by user if specified
        if user_id:
            sessions = [s for s in sessions if s.user_context.get("user_id") == user_id]
        
        # Sort by updated_at descending
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        
        return sessions[:limit]
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        now = datetime.now()
        expired_sessions = []
        
        for session_id, timeout in self.session_timeouts.items():
            if now > timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            logger.info("Cleaning up expired session", session_id=session_id)
            await self.delete_session(session_id)
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    async def _cleanup_loop(self):
        """Background task for cleaning up expired sessions"""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                await self.cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in cleanup loop", error=str(e))
    
    async def _persist_session(self, session: Session):
        """Persist session to database"""
        try:
            # Use a new database session
            db = next(get_db())
            
            # Check if session exists
            db_session = db.query(DBSessionModel).filter(
                DBSessionModel.session_id == session.session_id
            ).first()
            
            if db_session:
                # Update existing session
                db_session.user_prompt = session.user_prompt
                db_session.current_step = session.current_step
                db_session.status = session.status.value
                db_session.user_context = session.user_context
                db_session.updated_at = session.updated_at
                db_session.completed_at = session.completed_at
                db_session.error_message = session.error_message
            else:
                # Create new session
                db_session = DBSessionModel(
                    session_id=session.session_id,
                    user_prompt=session.user_prompt,
                    current_step=session.current_step,
                    status=session.status.value,
                    user_context=session.user_context,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    completed_at=session.completed_at,
                    error_message=session.error_message
                )
                db.add(db_session)
            
            # Persist workflow steps
            for step in session.workflow_steps:
                db_step = db.query(DBWorkflowStep).filter(
                    DBWorkflowStep.session_id == session.session_id,
                    DBWorkflowStep.step_id == step.step_id
                ).first()
                
                if db_step:
                    # Update existing step
                    db_step.description = step.description
                    db_step.tool = step.tool
                    db_step.args = step.args
                    db_step.status = step.status.value
                    db_step.retry_count = step.retry_count
                    db_step.max_retries = step.max_retries
                    db_step.updated_at = step.updated_at
                else:
                    # Create new step
                    db_step = DBWorkflowStep(
                        session_id=session.session_id,
                        step_id=step.step_id,
                        description=step.description,
                        tool=step.tool,
                        args=step.args,
                        status=step.status.value,
                        retry_count=step.retry_count,
                        max_retries=step.max_retries,
                        created_at=step.created_at,
                        updated_at=step.updated_at
                    )
                    db.add(db_step)
            
            # Persist tool outputs
            for output in session.tool_outputs.values():
                db_output = db.query(DBToolOutput).filter(
                    DBToolOutput.session_id == session.session_id,
                    DBToolOutput.step_id == output.step_id
                ).first()
                
                if not db_output:
                    db_output = DBToolOutput(
                        session_id=session.session_id,
                        step_id=output.step_id,
                        tool=output.tool,
                        success=output.success,
                        output=output.output,
                        error=output.error,
                        execution_time=int(output.execution_time * 1000),  # Convert to milliseconds
                        timestamp=output.timestamp,
                        verification_passed=output.verification_passed
                    )
                    db.add(db_output)
            
            # Persist user approvals
            for approval in session.user_approvals:
                db_approval = db.query(DBUserApproval).filter(
                    DBUserApproval.session_id == session.session_id,
                    DBUserApproval.step_id == approval.step_id
                ).first()
                
                if not db_approval:
                    db_approval = DBUserApproval(
                        session_id=session.session_id,
                        step_id=approval.step_id,
                        approved=approval.approved,
                        feedback=approval.feedback,
                        timestamp=approval.timestamp,
                        user_id=approval.user_id
                    )
                    db.add(db_approval)
            
            db.commit()
            
        except Exception as e:
            logger.error("Failed to persist session", session_id=session.session_id, error=str(e))
            if 'db' in locals():
                db.rollback()
            raise
        finally:
            if 'db' in locals():
                db.close()
    
    async def _load_session_from_db(self, session_id: str) -> Optional[Session]:
        """Load session from database"""
        try:
            db = next(get_db())
            
            db_session = db.query(DBSessionModel).filter(
                DBSessionModel.session_id == session_id
            ).first()
            
            if not db_session:
                return None
            
            # Create session object
            session = Session(
                session_id=db_session.session_id,
                user_prompt=db_session.user_prompt,
                current_step=db_session.current_step,
                status=SessionStatus(db_session.status),
                user_context=db_session.user_context or {},
                created_at=db_session.created_at,
                updated_at=db_session.updated_at,
                completed_at=db_session.completed_at,
                error_message=db_session.error_message
            )
            
            # Load workflow steps
            for db_step in db_session.workflow_steps:
                step = WorkflowStep(
                    step_id=db_step.step_id,
                    description=db_step.description,
                    tool=db_step.tool,
                    args=db_step.args or {},
                    status=db_step.status,
                    retry_count=db_step.retry_count,
                    max_retries=db_step.max_retries,
                    created_at=db_step.created_at,
                    updated_at=db_step.updated_at
                )
                session.workflow_steps.append(step)
            
            # Load tool outputs
            for db_output in db_session.tool_outputs:
                output = ToolOutput(
                    tool=db_output.tool,
                    step_id=db_output.step_id,
                    success=db_output.success,
                    output=db_output.output,
                    error=db_output.error,
                    execution_time=db_output.execution_time / 1000.0,  # Convert from milliseconds
                    timestamp=db_output.timestamp,
                    verification_passed=db_output.verification_passed
                )
                session.tool_outputs[output.step_id] = output
            
            # Load user approvals
            for db_approval in db_session.user_approvals:
                approval = UserApproval(
                    step_id=db_approval.step_id,
                    approved=db_approval.approved,
                    feedback=db_approval.feedback,
                    timestamp=db_approval.timestamp,
                    user_id=db_approval.user_id
                )
                session.user_approvals.append(approval)
            
            return session
            
        except Exception as e:
            logger.error("Failed to load session from database", session_id=session_id, error=str(e))
            return None
        finally:
            if 'db' in locals():
                db.close()
    
    async def _delete_session_from_db(self, session_id: str):
        """Delete session from database"""
        try:
            db = next(get_db())
            
            db_session = db.query(DBSessionModel).filter(
                DBSessionModel.session_id == session_id
            ).first()
            
            if db_session:
                db.delete(db_session)
                db.commit()
                
        except Exception as e:
            logger.error("Failed to delete session from database", session_id=session_id, error=str(e))
            if 'db' in locals():
                db.rollback()
        finally:
            if 'db' in locals():
                db.close()
    
    async def _persist_all_sessions(self):
        """Persist all active sessions to database"""
        for session in self.active_sessions.values():
            await self._persist_session(session)
        
        logger.info(f"Persisted {len(self.active_sessions)} sessions to database")

# Global session manager instance
session_manager = SessionManager() 