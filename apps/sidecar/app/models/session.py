"""
Session state model for Sclip
Manages user sessions, tool outputs, approvals, and context
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum

class SessionStatus(Enum):
    """Session status enumeration"""
    AWAITING_PROMPT = "awaiting_prompt"
    PLANNING = "planning"
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class StepStatus(Enum):
    """Step status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFIED = "verified"
    NEEDS_APPROVAL = "needs_approval"

class UserApproval(BaseModel):
    """User approval/feedback for a step"""
    step_id: str
    approved: bool
    feedback: Optional[str] = None
    timestamp: datetime
    user_id: Optional[str] = None

class ToolOutput(BaseModel):
    """Output from a tool execution"""
    tool: str
    step_id: str
    success: bool
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float
    timestamp: datetime
    verification_passed: bool = False

class WorkflowStep(BaseModel):
    """A single step in the workflow"""
    step_id: str
    description: str
    tool: str
    args: Dict[str, Any]
    status: StepStatus = StepStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    output: Optional[ToolOutput] = None
    user_approval: Optional[UserApproval] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class Session(BaseModel):
    """
    Session state model for managing user sessions
    Contains all information needed to track and resume workflows
    """
    session_id: str
    user_prompt: str
    current_step: Optional[str] = None
    workflow_steps: List[WorkflowStep] = []
    tool_outputs: Dict[str, ToolOutput] = {}
    user_approvals: List[UserApproval] = []
    retry_counts: Dict[str, int] = {}
    status: SessionStatus = SessionStatus.AWAITING_PROMPT
    user_context: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def add_step(self, step: WorkflowStep):
        """Add a new step to the workflow"""
        self.workflow_steps.append(step)
        self.updated_at = datetime.now()
    
    def update_step_status(self, step_id: str, status: StepStatus):
        """Update the status of a specific step"""
        for step in self.workflow_steps:
            if step.step_id == step_id:
                step.status = status
                step.updated_at = datetime.now()
                break
        self.updated_at = datetime.now()
    
    def add_tool_output(self, output: ToolOutput):
        """Add tool output to the session"""
        self.tool_outputs[output.step_id] = output
        
        # Update corresponding step
        for step in self.workflow_steps:
            if step.step_id == output.step_id:
                step.output = output
                step.updated_at = datetime.now()
                break
        
        self.updated_at = datetime.now()
    
    def add_user_approval(self, approval: UserApproval):
        """Add user approval/feedback"""
        self.user_approvals.append(approval)
        
        # Update corresponding step
        for step in self.workflow_steps:
            if step.step_id == approval.step_id:
                step.user_approval = approval
                step.updated_at = datetime.now()
                break
        
        self.updated_at = datetime.now()
    
    def get_current_step(self) -> Optional[WorkflowStep]:
        """Get the current step being executed"""
        if self.current_step:
            for step in self.workflow_steps:
                if step.step_id == self.current_step:
                    return step
        return None
    
    def get_next_pending_step(self) -> Optional[WorkflowStep]:
        """Get the next pending step"""
        for step in self.workflow_steps:
            if step.status == StepStatus.PENDING:
                return step
        return None
    
    def get_completed_steps(self) -> List[WorkflowStep]:
        """Get all completed steps"""
        return [step for step in self.workflow_steps if step.status == StepStatus.COMPLETED]
    
    def get_failed_steps(self) -> List[WorkflowStep]:
        """Get all failed steps"""
        return [step for step in self.workflow_steps if step.status == StepStatus.FAILED]
    
    def get_progress_percentage(self) -> int:
        """Calculate progress percentage"""
        if not self.workflow_steps:
            return 0
        
        completed = len(self.get_completed_steps())
        total = len(self.workflow_steps)
        return int((completed / total) * 100)
    
    def is_complete(self) -> bool:
        """Check if the session is complete"""
        return self.status == SessionStatus.COMPLETED
    
    def is_failed(self) -> bool:
        """Check if the session has failed"""
        return self.status == SessionStatus.FAILED
    
    def can_retry_step(self, step_id: str) -> bool:
        """Check if a step can be retried"""
        for step in self.workflow_steps:
            if step.step_id == step_id:
                return step.retry_count < step.max_retries
        return False
    
    def increment_retry_count(self, step_id: str):
        """Increment retry count for a step"""
        for step in self.workflow_steps:
            if step.step_id == step_id:
                step.retry_count += 1
                step.updated_at = datetime.now()
                break
        self.updated_at = datetime.now()
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get a summary of the session"""
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "user_prompt": self.user_prompt,
            "current_step": self.current_step,
            "total_steps": len(self.workflow_steps),
            "completed_steps": len(self.get_completed_steps()),
            "failed_steps": len(self.get_failed_steps()),
            "progress_percentage": self.get_progress_percentage(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message
        } 