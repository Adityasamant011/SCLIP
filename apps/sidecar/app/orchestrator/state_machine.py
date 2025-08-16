"""
State Machine for SclipBrain Orchestrator
Manages state transitions and ensures proper workflow flow
"""
from enum import Enum
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from apps.sidecar.app.utils.logger import get_logger

logger = get_logger(__name__)

class OrchestratorState(Enum):
    """State machine states for the orchestrator"""
    AWAITING_PROMPT = "awaiting_prompt"
    PLANNING = "planning"
    EXECUTING_STEP = "executing_step"
    VERIFYING_STEP = "verifying_step"
    AWAITING_USER_APPROVAL = "awaiting_user_approval"
    HANDLING_ERROR = "handling_error"
    FINAL_CHECK = "final_check"
    DONE = "done"
    PAUSED = "paused"

@dataclass
class StateTransition:
    """Represents a valid state transition"""
    from_state: OrchestratorState
    to_state: OrchestratorState
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    description: str = ""

class StateMachine:
    """
    State machine for managing orchestrator workflow states
    Ensures proper transitions and maintains workflow integrity
    """
    
    def __init__(self):
        self.current_state = OrchestratorState.AWAITING_PROMPT
        self.state_history: List[OrchestratorState] = []
        self.context: Dict[str, Any] = {}
        
        # Define valid state transitions
        self.transitions = self._define_transitions()
        
        logger.info("State machine initialized", initial_state=self.current_state.value)
    
    def _define_transitions(self) -> List[StateTransition]:
        """Define all valid state transitions"""
        return [
            # Initial workflow start
            StateTransition(
                OrchestratorState.AWAITING_PROMPT,
                OrchestratorState.PLANNING,
                description="User prompt received, starting planning"
            ),
            
            # Planning phase
            StateTransition(
                OrchestratorState.PLANNING,
                OrchestratorState.EXECUTING_STEP,
                description="Planning complete, starting execution"
            ),
            StateTransition(
                OrchestratorState.PLANNING,
                OrchestratorState.HANDLING_ERROR,
                description="Planning failed, handling error"
            ),
            
            # Execution phase
            StateTransition(
                OrchestratorState.EXECUTING_STEP,
                OrchestratorState.VERIFYING_STEP,
                description="Step execution complete, verifying result"
            ),
            StateTransition(
                OrchestratorState.EXECUTING_STEP,
                OrchestratorState.HANDLING_ERROR,
                description="Step execution failed, handling error"
            ),
            StateTransition(
                OrchestratorState.EXECUTING_STEP,
                OrchestratorState.PAUSED,
                description="User requested pause during execution"
            ),
            
            # Verification phase
            StateTransition(
                OrchestratorState.VERIFYING_STEP,
                OrchestratorState.EXECUTING_STEP,
                lambda ctx: ctx.get("verification_passed", False),
                description="Verification passed, continuing to next step"
            ),
            StateTransition(
                OrchestratorState.VERIFYING_STEP,
                OrchestratorState.HANDLING_ERROR,
                lambda ctx: not ctx.get("verification_passed", True),
                description="Verification failed, handling error"
            ),
            
            # Error handling
            StateTransition(
                OrchestratorState.HANDLING_ERROR,
                OrchestratorState.EXECUTING_STEP,
                lambda ctx: ctx.get("retry_available", False),
                description="Retry available, retrying step"
            ),
            StateTransition(
                OrchestratorState.HANDLING_ERROR,
                OrchestratorState.AWAITING_USER_APPROVAL,
                lambda ctx: not ctx.get("retry_available", True),
                description="No retries left, awaiting user approval"
            ),
            
            # User approval
            StateTransition(
                OrchestratorState.AWAITING_USER_APPROVAL,
                OrchestratorState.EXECUTING_STEP,
                lambda ctx: ctx.get("user_approved", False),
                description="User approved, resuming execution"
            ),
            StateTransition(
                OrchestratorState.AWAITING_USER_APPROVAL,
                OrchestratorState.DONE,
                lambda ctx: ctx.get("user_cancelled", False),
                description="User cancelled, ending workflow"
            ),
            
            # Pause/Resume
            StateTransition(
                OrchestratorState.PAUSED,
                OrchestratorState.EXECUTING_STEP,
                description="User resumed, continuing execution"
            ),
            
            # Final check
            StateTransition(
                OrchestratorState.EXECUTING_STEP,
                OrchestratorState.FINAL_CHECK,
                lambda ctx: ctx.get("all_steps_complete", False),
                description="All steps complete, performing final check"
            ),
            StateTransition(
                OrchestratorState.FINAL_CHECK,
                OrchestratorState.DONE,
                lambda ctx: ctx.get("final_check_passed", False),
                description="Final check passed, workflow complete"
            ),
            StateTransition(
                OrchestratorState.FINAL_CHECK,
                OrchestratorState.AWAITING_USER_APPROVAL,
                lambda ctx: not ctx.get("final_check_passed", True),
                description="Final check failed, awaiting user approval"
            ),
            
            # Terminal state
            StateTransition(
                OrchestratorState.DONE,
                OrchestratorState.AWAITING_PROMPT,
                description="Workflow complete, ready for new prompt"
            )
        ]
    
    def can_transition_to(self, new_state: OrchestratorState, context: Dict[str, Any] = None) -> bool:
        """Check if transition to new state is valid"""
        context = context or {}
        
        for transition in self.transitions:
            if (transition.from_state == self.current_state and 
                transition.to_state == new_state):
                
                # Check condition if present
                if transition.condition:
                    return transition.condition(context)
                return True
        
        return False
    
    def transition_to(self, new_state: OrchestratorState, context: Dict[str, Any] = None) -> bool:
        """Attempt to transition to a new state"""
        context = context or {}
        
        if not self.can_transition_to(new_state, context):
            logger.warning("Invalid state transition attempted",
                          from_state=self.current_state.value,
                          to_state=new_state.value)
            return False
        
        # Find the transition
        transition = None
        for t in self.transitions:
            if (t.from_state == self.current_state and 
                t.to_state == new_state):
                transition = t
                break
        
        if transition:
            # Update state
            old_state = self.current_state
            self.current_state = new_state
            self.state_history.append(old_state)
            self.context.update(context)
            
            logger.info("State transition successful",
                       from_state=old_state.value,
                       to_state=new_state.value,
                       description=transition.description)
            return True
        
        return False
    
    def get_valid_transitions(self, context: Dict[str, Any] = None) -> List[OrchestratorState]:
        """Get list of valid next states"""
        context = context or {}
        valid_states = []
        
        for transition in self.transitions:
            if transition.from_state == self.current_state:
                if transition.condition:
                    if transition.condition(context):
                        valid_states.append(transition.to_state)
                else:
                    valid_states.append(transition.to_state)
        
        return valid_states
    
    def get_state_info(self) -> Dict[str, Any]:
        """Get current state information"""
        return {
            "current_state": self.current_state.value,
            "state_history": [state.value for state in self.state_history],
            "valid_transitions": [state.value for state in self.get_valid_transitions()],
            "context": self.context
        }
    
    def reset(self):
        """Reset state machine to initial state"""
        self.current_state = OrchestratorState.AWAITING_PROMPT
        self.state_history = []
        self.context = {}
        logger.info("State machine reset")
    
    def is_terminal_state(self) -> bool:
        """Check if current state is terminal"""
        return self.current_state in [OrchestratorState.DONE]
    
    def is_error_state(self) -> bool:
        """Check if current state indicates an error"""
        return self.current_state in [OrchestratorState.HANDLING_ERROR]
    
    def is_waiting_for_user(self) -> bool:
        """Check if current state is waiting for user input"""
        return self.current_state in [
            OrchestratorState.AWAITING_USER_APPROVAL,
            OrchestratorState.AWAITING_PROMPT
        ] 