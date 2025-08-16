"""
Agentic Workflow Orchestrator for Sclip
Implements sophisticated planning and execution patterns for video creation
"""
import asyncio
import json
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from ..utils.logger import get_logger
from ..core.context_manager import context_manager
from ..tools.mcp_protocol import mcp_protocol, MCPMessage, MCPMessageType

logger = get_logger(__name__)

class WorkflowState(Enum):
    """Workflow execution states"""
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

class WorkflowStep(Enum):
    """Workflow step types"""
    ANALYZE_REQUEST = "analyze_request"
    PLAN_WORKFLOW = "plan_workflow"
    EXECUTE_TOOL = "execute_tool"
    VALIDATE_RESULT = "validate_result"
    ITERATE = "iterate"
    COMPLETE = "complete"

@dataclass
class WorkflowStep:
    """Individual workflow step"""
    id: str
    type: WorkflowStep
    tool_name: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    dependencies: List[str] = None

@dataclass
class WorkflowPlan:
    """Complete workflow plan"""
    id: str
    user_request: str
    steps: List[WorkflowStep]
    estimated_duration: float
    priority: str = "normal"
    created_at: float = None

class AgenticWorkflowOrchestrator:
    """
    Advanced agentic workflow orchestrator
    Implements sophisticated planning and execution patterns
    """
    
    def __init__(self):
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        self.workflow_history: List[Dict[str, Any]] = []
        self.execution_metrics: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Agentic Workflow Orchestrator initialized")
    
    async def create_workflow(self, session_id: str, user_request: str, websocket_manager=None) -> str:
        """Create a new agentic workflow"""
        workflow_id = f"workflow_{session_id}_{int(asyncio.get_event_loop().time())}"
        
        # Initialize workflow
        workflow = {
            "id": workflow_id,
            "session_id": session_id,
            "user_request": user_request,
            "state": WorkflowState.PLANNING,
            "plan": None,
            "current_step": 0,
            "steps": [],
            "context": {},
            "created_at": asyncio.get_event_loop().time(),
            "started_at": None,
            "completed_at": None,
            "websocket_manager": websocket_manager
        }
        
        self.active_workflows[workflow_id] = workflow
        
        # Send initial status
        if websocket_manager:
            await self._send_workflow_status(workflow_id, "Workflow created, starting analysis...")
        
        logger.info(f"Created workflow {workflow_id} for request: {user_request[:50]}...")
        return workflow_id
    
    async def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Execute the complete agentic workflow"""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        websocket_manager = workflow.get("websocket_manager")
        
        try:
            workflow["state"] = WorkflowState.PLANNING
            workflow["started_at"] = asyncio.get_event_loop().time()
            
            # Step 1: Analyze user request
            if websocket_manager:
                await self._send_workflow_status(workflow_id, "Analyzing user request...")
            analysis = await self._analyze_request(workflow)
            
            # Step 2: Create execution plan
            if websocket_manager:
                await self._send_workflow_status(workflow_id, "Creating execution plan...")
            plan = await self._create_execution_plan(workflow, analysis)
            workflow["plan"] = plan
            
            # Step 3: Execute workflow steps
            workflow["state"] = WorkflowState.EXECUTING
            if websocket_manager:
                await self._send_workflow_status(workflow_id, f"Executing {len(plan.steps)} steps...")
            
            results = await self._execute_workflow_steps(workflow_id, plan)
            
            # Step 4: Validate and iterate if needed
            if not self._validate_workflow_results(results):
                if websocket_manager:
                    await self._send_workflow_status(workflow_id, "Results validation failed, iterating...")
                results = await self._iterate_workflow(workflow_id, results)
            
            # Step 5: Complete workflow
            workflow["state"] = WorkflowState.COMPLETED
            workflow["completed_at"] = asyncio.get_event_loop().time()
            
            final_result = await self._finalize_workflow(workflow_id, results)
            
            # Log completion
            self._log_workflow_completion(workflow_id, final_result)
            
            if websocket_manager:
                await self._send_workflow_status(workflow_id, "Workflow completed successfully!")
            
            return final_result
            
        except Exception as e:
            workflow["state"] = WorkflowState.FAILED
            workflow["error"] = str(e)
            
            if websocket_manager:
                await self._send_workflow_status(workflow_id, f"Workflow failed: {str(e)}")
            logger.error(f"Workflow {workflow_id} failed: {e}")
            
            raise
    
    async def _analyze_request(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user request to understand intent and requirements"""
        user_request = workflow["user_request"]
        session_id = workflow["session_id"]
        
        # Get enhanced context
        context = context_manager.get_enhanced_context_for_ai(session_id, user_request)
        
        # Create analysis prompt
        analysis_prompt = f"""
**REQUEST ANALYSIS**

**User Request:** {user_request}

**Context:**
{context}

**Analysis Tasks:**
1. Identify the primary intent (script creation, video generation, editing, etc.)
2. Extract key parameters (topic, style, length, effects, etc.)
3. Determine required tools and their sequence
4. Assess complexity and estimate effort
5. Identify potential challenges or edge cases

**Available Tools:**
{mcp_protocol.format_tools_for_llm()}

Please provide a structured analysis in JSON format:
{{
    "intent": "primary user intent",
    "parameters": {{"key": "value"}},
    "required_tools": ["tool1", "tool2"],
    "estimated_steps": 5,
    "complexity": "low|medium|high",
    "challenges": ["challenge1", "challenge2"],
    "success_criteria": ["criteria1", "criteria2"]
}}
"""
        
        # Send analysis request to LLM
        # This would integrate with your existing LLM service
        # For now, return a basic analysis
        return {
            "intent": "video_creation",
            "parameters": {"topic": "user_request", "style": "cinematic"},
            "required_tools": ["script_writer", "broll_finder", "voiceover_generator", "video_processor"],
            "estimated_steps": 4,
            "complexity": "medium",
            "challenges": ["media_quality", "timing_sync"],
            "success_criteria": ["script_created", "media_downloaded", "video_generated"]
        }
    
    async def _create_execution_plan(self, workflow: Dict[str, Any], analysis: Dict[str, Any]) -> WorkflowPlan:
        """Create detailed execution plan based on analysis"""
        plan_id = f"plan_{workflow['id']}"
        steps = []
        
        # Create steps based on required tools
        required_tools = analysis.get("required_tools", [])
        
        for i, tool_name in enumerate(required_tools):
            step = WorkflowStep(
                id=f"step_{i+1}",
                type=WorkflowStep.EXECUTE_TOOL,
                tool_name=tool_name,
                parameters=analysis.get("parameters", {}),
                dependencies=[f"step_{j+1}" for j in range(i)] if i > 0 else []
            )
            steps.append(step)
        
        # Add validation and completion steps
        validation_step = WorkflowStep(
            id="step_validation",
            type=WorkflowStep.VALIDATE_RESULT,
            dependencies=[step.id for step in steps]
        )
        steps.append(validation_step)
        
        completion_step = WorkflowStep(
            id="step_completion",
            type=WorkflowStep.COMPLETE,
            dependencies=["step_validation"]
        )
        steps.append(completion_step)
        
        return WorkflowPlan(
            id=plan_id,
            user_request=workflow["user_request"],
            steps=steps,
            estimated_duration=len(steps) * 30,  # 30 seconds per step
            created_at=asyncio.get_event_loop().time()
        )
    
    async def _execute_workflow_steps(self, workflow_id: str, plan: WorkflowPlan) -> Dict[str, Any]:
        """Execute workflow steps with proper dependency management"""
        workflow = self.active_workflows[workflow_id]
        websocket_manager = workflow.get("websocket_manager")
        results = {}
        
        for step in plan.steps:
            # Check dependencies
            if not self._check_step_dependencies(step, results):
                if websocket_manager:
                    await self._send_workflow_status(workflow_id, f"Waiting for dependencies: {step.id}")
                continue
            
            # Execute step
            if websocket_manager:
                await self._send_workflow_status(workflow_id, f"Executing step: {step.id}")
            
            try:
                step.start_time = asyncio.get_event_loop().time()
                step.status = "executing"
                
                if step.type == WorkflowStep.EXECUTE_TOOL:
                    result = await self._execute_tool_step(workflow_id, step)
                elif step.type == WorkflowStep.VALIDATE_RESULT:
                    result = await self._execute_validation_step(workflow_id, step, results)
                elif step.type == WorkflowStep.COMPLETE:
                    result = await self._execute_completion_step(workflow_id, step, results)
                else:
                    result = {"success": True, "message": "Step completed"}
                
                step.end_time = asyncio.get_event_loop().time()
                step.status = "completed"
                step.result = result
                
                results[step.id] = result
                
                # Update progress
                progress = (len([s for s in plan.steps if s.status == "completed"]) / len(plan.steps)) * 100
                if websocket_manager:
                    await self._send_workflow_progress(workflow_id, progress)
                
            except Exception as e:
                step.status = "failed"
                step.error = str(e)
                step.end_time = asyncio.get_event_loop().time()
                
                if websocket_manager:
                    await self._send_workflow_status(workflow_id, f"Step {step.id} failed: {str(e)}")
                logger.error(f"Step {step.id} failed: {e}")
                
                # Decide whether to continue or fail
                if not self._should_continue_on_failure(step):
                    raise e
        
        return results
    
    async def _execute_tool_step(self, workflow_id: str, step: WorkflowStep) -> Dict[str, Any]:
        """Execute a tool step"""
        workflow = self.active_workflows[workflow_id]
        session_id = workflow["session_id"]
        websocket_manager = workflow.get("websocket_manager")
        
        # Create MCP tool call
        mcp_message = mcp_protocol.create_tool_call_message(
            step.tool_name,
            step.parameters or {}
        )
        
        # Send tool call to frontend
        if websocket_manager:
            await websocket_manager.send_message(session_id, {
                "type": "tool_call",
                "tool": step.tool_name,
                "args": step.parameters,
                "description": f"Executing {step.tool_name}",
                "timestamp": datetime.now().isoformat()
            })
        
        # Execute tool (this would integrate with your existing tool execution)
        # For now, simulate execution
        await asyncio.sleep(2)  # Simulate tool execution time
        
        result = {
            "success": True,
            "tool": step.tool_name,
            "result": f"Simulated result for {step.tool_name}",
            "execution_time": 2.0
        }
        
        # Send tool result to frontend
        if websocket_manager:
            await websocket_manager.send_message(session_id, {
                "type": "tool_result",
                "tool": step.tool_name,
                "success": result["success"],
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
        
        return result
    
    async def _execute_validation_step(self, workflow_id: str, step: WorkflowStep, results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute validation step"""
        # Validate that all required results are present and successful
        required_results = ["script_created", "media_downloaded", "voiceover_created"]
        validation_results = []
        
        for required in required_results:
            if required in results:
                validation_results.append(f"✓ {required}")
            else:
                validation_results.append(f"✗ {required} missing")
        
        return {
            "success": len([r for r in validation_results if r.startswith("✓")]) == len(required_results),
            "validation_results": validation_results
        }
    
    async def _execute_completion_step(self, workflow_id: str, step: WorkflowStep, results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute completion step"""
        workflow = self.active_workflows[workflow_id]
        
        # Compile final results
        final_result = {
            "workflow_id": workflow_id,
            "user_request": workflow["user_request"],
            "execution_time": asyncio.get_event_loop().time() - workflow["started_at"],
            "steps_completed": len([s for s in workflow["plan"].steps if s.status == "completed"]),
            "total_steps": len(workflow["plan"].steps),
            "results": results
        }
        
        return final_result
    
    def _check_step_dependencies(self, step: WorkflowStep, results: Dict[str, Any]) -> bool:
        """Check if step dependencies are satisfied"""
        for dep_id in step.dependencies or []:
            if dep_id not in results:
                return False
        return True
    
    def _should_continue_on_failure(self, step: WorkflowStep) -> bool:
        """Determine if workflow should continue after step failure"""
        # Critical steps that should cause workflow failure
        critical_steps = ["script_writer", "video_processor"]
        
        if step.tool_name in critical_steps:
            return False
        
        return True
    
    def _validate_workflow_results(self, results: Dict[str, Any]) -> bool:
        """Validate workflow results"""
        # Check if all critical results are present and successful
        critical_results = ["script_created", "video_generated"]
        
        for result_key in critical_results:
            if result_key not in results:
                return False
            
            result = results[result_key]
            if not result.get("success", False):
                return False
        
        return True
    
    async def _iterate_workflow(self, workflow_id: str, previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """Iterate workflow based on previous results"""
        # This would implement sophisticated iteration logic
        # For now, return the previous results
        return previous_results
    
    async def _finalize_workflow(self, workflow_id: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize workflow and prepare final output"""
        workflow = self.active_workflows[workflow_id]
        
        # Update workflow with final results
        workflow["final_results"] = results
        
        # Send final GUI updates
        session_id = workflow["session_id"]
        await self._send_final_gui_updates(session_id, results)
        
        return results
    
    async def _send_workflow_status(self, workflow_id: str, message: str):
        """Send workflow status update"""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return
        
        session_id = workflow["session_id"]
        websocket_manager = workflow.get("websocket_manager")
        if websocket_manager:
            await websocket_manager.send_message(session_id, {
                "type": "workflow_status",
                "workflow_id": workflow_id,
                "message": message,
                "state": workflow["state"].value,
                "timestamp": datetime.now().isoformat()
            })
    
    async def _send_workflow_progress(self, workflow_id: str, progress: float):
        """Send workflow progress update"""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return
        
        session_id = workflow["session_id"]
        websocket_manager = workflow.get("websocket_manager")
        if websocket_manager:
            await websocket_manager.send_message(session_id, {
                "type": "workflow_progress",
                "workflow_id": workflow_id,
                "progress": progress,
                "timestamp": datetime.now().isoformat()
            })
    
    async def _send_final_gui_updates(self, session_id: str, results: Dict[str, Any]):
        """Send final GUI updates based on workflow results"""
        # This would send the appropriate GUI updates based on the results
        # Similar to the existing video orchestrator logic
        pass
    
    def _log_workflow_completion(self, workflow_id: str, results: Dict[str, Any]):
        """Log workflow completion for analytics"""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return
        
        completion_log = {
            "workflow_id": workflow_id,
            "session_id": workflow["session_id"],
            "user_request": workflow["user_request"],
            "execution_time": results.get("execution_time", 0),
            "steps_completed": results.get("steps_completed", 0),
            "total_steps": results.get("total_steps", 0),
            "success": workflow["state"] == WorkflowState.COMPLETED,
            "created_at": workflow["created_at"],
            "completed_at": workflow["completed_at"]
        }
        
        self.workflow_history.append(completion_log)
        
        # Keep only last 100 workflows
        if len(self.workflow_history) > 100:
            self.workflow_history = self.workflow_history[-100:]
        
        logger.info(f"Workflow {workflow_id} completed: {completion_log}")

# Global orchestrator instance
agentic_orchestrator = AgenticWorkflowOrchestrator() 