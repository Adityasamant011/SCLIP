"""
Streaming Manager for Real-Time AI Response Streaming
Handles character-by-character streaming with natural typing effects
"""

import asyncio
import json
from typing import Dict, Any, AsyncGenerator, Optional, List
from datetime import datetime
import uuid

class StreamingManager:
    """
    Manages real-time streaming of AI responses with natural typing effects.
    Supports both word-by-word and character-by-character streaming.
    """
    
    def __init__(self, session_id: str, send_message_func):
        self.session_id = session_id
        self.send_message = send_message_func
        self.streaming_tasks = {}
        
    async def stream_ai_response(
        self, 
        content: str, 
        message_type: str = "ai_message",
        streaming_mode: str = "character",  # "character" or "word"
        speed: int = 25,  # milliseconds per character/word
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream an AI response with natural typing effects.
        
        Args:
            content: The full text content to stream
            message_type: Type of message (ai_message, informational, etc.)
            streaming_mode: "character" for char-by-char, "word" for word-by-word
            speed: Delay between characters/words in milliseconds
            **kwargs: Additional message properties
        """
        
        if not content:
            return
            
        # Send initial "thinking" state
        await self.send_message({
            "type": "thinking",
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "message_id": str(uuid.uuid4())
        })
        
        # Create a single message ID for the entire response
        message_id = str(uuid.uuid4())
        
        if streaming_mode == "character":
            # Character-by-character streaming - update same message
            streamed_text = ""
            for i, char in enumerate(content):
                streamed_text += char
                
                # Send partial message with same ID
                message = {
                    "type": message_type,
                    "content": streamed_text,
                    "session_id": self.session_id,
                    "timestamp": datetime.now().isoformat(),
                    "message_id": message_id,  # Same ID for all updates
                    "is_partial": True,
                    "progress": (i + 1) / len(content),
                    **kwargs
                }
                
                yield message
                await self.send_message(message)
                
                # Natural delays for punctuation and spaces
                if char in ['.', '!', '?', ',', ';', ':']:
                    await asyncio.sleep(0.05)  # Longer pause for punctuation
                elif char == ' ':
                    await asyncio.sleep(0.01)  # Shorter pause for spaces
                else:
                    await asyncio.sleep(0.02)  # Normal character delay
                    
        elif streaming_mode == "word":
            # Word-by-word streaming - update same message
            words = content.split()
            streamed_text = ""
            
            for i, word in enumerate(words):
                streamed_text += word + (" " if i < len(words) - 1 else "")
                
                # Send partial message with same ID
                message = {
                    "type": message_type,
                    "content": streamed_text,
                    "session_id": self.session_id,
                    "timestamp": datetime.now().isoformat(),
                    "message_id": message_id,  # Same ID for all updates
                    "is_partial": True,
                    "progress": (i + 1) / len(words),
                    **kwargs
                }
                
                yield message
                await self.send_message(message)
                
                # Natural delays for different word types
                if word.endswith(('.', '!', '?')):
                    await asyncio.sleep(0.1)  # Longer pause for sentence endings
                elif word.endswith((',', ';', ':')):
                    await asyncio.sleep(0.05)  # Medium pause for punctuation
                else:
                    await asyncio.sleep(0.03)  # Normal word delay
        
        # Send final complete message
        final_message = {
            "type": message_type,
            "content": content,
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "message_id": message_id,
            "is_partial": False,
            "progress": 1.0,
            **kwargs
        }
        
        yield final_message
        await self.send_message(final_message)
    
    async def stream_agentic_reasoning(
        self,
        reasoning_steps: List[str],
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream agentic reasoning process in real-time.
        Shows the AI's step-by-step thinking process.
        """
        message_id = str(uuid.uuid4())
        
        for i, reasoning_step in enumerate(reasoning_steps):
            # Send reasoning step
            reasoning_message = {
                "type": "reasoning",
                "content": reasoning_step,
                "step_number": i + 1,
                "total_steps": len(reasoning_steps),
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "message_id": f"{message_id}_step_{i+1}",
                **kwargs
            }
            
            yield reasoning_message
            await self.send_message(reasoning_message)
            
            # Pause between reasoning steps
            await asyncio.sleep(0.5)
    
    async def stream_tool_execution(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        description: str,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream tool execution process with real-time updates.
        """
        message_id = str(uuid.uuid4())
        
        # Step 1: Announce tool execution
        execution_message = {
            "type": "tool_execution_start",
            "tool": tool_name,
            "args": tool_args,
            "description": description,
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "message_id": message_id,
            **kwargs
        }
        
        yield execution_message
        await self.send_message(execution_message)
        
        # Step 2: Show progress updates
        progress_steps = [
            "Initializing tool...",
            "Processing request...",
            "Executing operation...",
            "Finalizing results..."
        ]
        
        for i, progress_step in enumerate(progress_steps):
            progress_message = {
                "type": "tool_progress",
                "tool": tool_name,
                "status": progress_step,
                "progress": (i + 1) / len(progress_steps),
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "message_id": f"{message_id}_progress_{i+1}",
                **kwargs
            }
            
            yield progress_message
            await self.send_message(progress_message)
            
            # Simulate processing time
            await asyncio.sleep(0.3)
        
        # Step 3: Tool execution complete
        complete_message = {
            "type": "tool_execution_complete",
            "tool": tool_name,
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "message_id": f"{message_id}_complete",
            **kwargs
        }
        
        yield complete_message
        await self.send_message(complete_message)
    
    async def stream_decision_making(
        self,
        context: Dict[str, Any],
        options: List[str],
        decision: str,
        reasoning: str,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream AI decision-making process.
        Shows context analysis, options considered, and final decision.
        """
        message_id = str(uuid.uuid4())
        
        # Step 1: Context analysis
        context_message = {
            "type": "decision_context",
            "context": context,
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "message_id": f"{message_id}_context",
            **kwargs
        }
        
        yield context_message
        await self.send_message(context_message)
        
        # Step 2: Options considered
        for i, option in enumerate(options):
            option_message = {
                "type": "decision_option",
                "option": option,
                "option_number": i + 1,
                "total_options": len(options),
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "message_id": f"{message_id}_option_{i+1}",
                **kwargs
            }
            
            yield option_message
            await self.send_message(option_message)
            
            await asyncio.sleep(0.2)
        
        # Step 3: Final decision
        decision_message = {
            "type": "decision_made",
            "decision": decision,
            "reasoning": reasoning,
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "message_id": f"{message_id}_decision",
            **kwargs
        }
        
        yield decision_message
        await self.send_message(decision_message)
    
    async def stream_with_tool_calls(
        self, 
        ai_response: str, 
        tool_calls: list = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream AI response with embedded tool calls.
        Shows AI thinking, then tool execution, then results.
        """
        
        # Stream the AI response first
        async for message in self.stream_ai_response(ai_response, **kwargs):
            yield message
        
        if tool_calls:
            for tool_call in tool_calls:
                # Send tool call notification
                tool_message = {
                    "type": "tool_call",
                    "tool": tool_call.get("tool", ""),
                    "args": tool_call.get("args", {}),
                    "step": tool_call.get("step", ""),
                    "description": tool_call.get("description", ""),
                    "session_id": self.session_id,
                    "timestamp": datetime.now().isoformat(),
                    "message_id": str(uuid.uuid4())
                }
                
                yield tool_message
                await self.send_message(tool_message)
                
                # Simulate tool execution time
                await asyncio.sleep(1)
                
                # Send tool result (placeholder - would be actual result)
                result_message = {
                    "type": "tool_result",
                    "tool": tool_call.get("tool", ""),
                    "step": tool_call.get("step", ""),
                    "result": tool_call.get("result", {}),
                    "success": tool_call.get("success", True),
                    "session_id": self.session_id,
                    "timestamp": datetime.now().isoformat(),
                    "message_id": str(uuid.uuid4())
                }
                
                yield result_message
                await self.send_message(result_message)
    
    async def stream_progress_updates(
        self, 
        steps: list, 
        current_step: int = 0
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream progress updates for workflow execution.
        """
        for i, step in enumerate(steps):
            progress_message = {
                "type": "progress",
                "step": step.get("step_id", f"step_{i+1}"),
                "description": step.get("description", ""),
                "percent": int(100 * (i + 1) / len(steps)),
                "status": f"Executing step {i+1}/{len(steps)}",
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "message_id": str(uuid.uuid4())
            }
            
            yield progress_message
            await self.send_message(progress_message)
            
            # Simulate step execution time
            await asyncio.sleep(0.5)
    
    def create_streaming_task(self, task_id: str, coroutine) -> str:
        """Create a new streaming task"""
        if task_id in self.streaming_tasks:
            # Cancel existing task
            self.cancel_streaming_task(task_id)
        
        # Create new task
        task = asyncio.create_task(coroutine)
        self.streaming_tasks[task_id] = task
        return task_id
    
    def cancel_streaming_task(self, task_id: str) -> bool:
        """Cancel a streaming task"""
        if task_id in self.streaming_tasks:
            task = self.streaming_tasks[task_id]
            if not task.done():
                task.cancel()
            del self.streaming_tasks[task_id]
            return True
        return False
    
    def cleanup(self):
        """Clean up all streaming tasks"""
        for task_id in list(self.streaming_tasks.keys()):
            self.cancel_streaming_task(task_id) 