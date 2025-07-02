"""
Base agent class with ReAct reasoning and communication capabilities.
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, AsyncGenerator
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_engine import BaseLLM, PromptBuilder, FunctionCaller
from memory.vector_memory import VectorMemory


class AgentState(Enum):
    """Agent execution states."""
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    WAITING = "waiting"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class AgentMessage:
    """Message between agents."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    recipient: str = ""
    content: str = ""
    message_type: str = "text"
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AgentThought:
    """Agent reasoning step."""
    observation: str
    thought: str
    action: str
    action_input: Dict[str, Any]
    result: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


class BaseAgent(ABC):
    """Abstract base class for all agents."""
    
    def __init__(
        self,
        name: str,
        llm: BaseLLM,
        memory: VectorMemory,
        role_description: str = "",
        max_iterations: int = 10
    ):
        self.name = name
        self.llm = llm
        self.memory = memory
        self.role_description = role_description
        self.max_iterations = max_iterations
        
        self.state = AgentState.IDLE
        self.current_task: Optional[str] = None
        self.thoughts: List[AgentThought] = []
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.function_caller = FunctionCaller()
        self.prompt_builder = PromptBuilder()
        
        # Agent capabilities
        self.capabilities: List[str] = []
        self.tools: Dict[str, Any] = {}
        
        # Communication
        self.subscribers: List[str] = []
        self.message_bus: Optional[Any] = None
        
        self._setup_functions()
    
    @abstractmethod
    def _setup_functions(self) -> None:
        """Setup agent-specific functions."""
        pass
    
    @abstractmethod
    async def _think(self, observation: str) -> AgentThought:
        """Generate reasoning step."""
        pass
    
    @abstractmethod
    async def _act(self, thought: AgentThought) -> str:
        """Execute action based on thought."""
        pass
    
    async def process_task(self, task: str, context: Dict[str, Any] = None) -> str:
        """Process a task using ReAct reasoning loop."""
        self.current_task = task
        self.state = AgentState.THINKING
        self.thoughts.clear()
        
        context = context or {}
        observation = f"Task: {task}\nContext: {context}"
        
        try:
            for iteration in range(self.max_iterations):
                # Think
                thought = await self._think(observation)
                self.thoughts.append(thought)
                
                # Check if task is complete
                if thought.action.lower() in ["complete", "finish", "done"]:
                    self.state = AgentState.COMPLETED
                    return thought.result or "Task completed successfully"
                
                # Act
                self.state = AgentState.ACTING
                result = await self._act(thought)
                thought.result = result
                
                # Update observation for next iteration
                observation = f"Previous action result: {result}"
                
                # Store thought in memory
                await self._store_thought(thought)
            
            self.state = AgentState.COMPLETED
            return "Task completed after maximum iterations"
            
        except Exception as e:
            self.state = AgentState.ERROR
            error_msg = f"Error processing task: {str(e)}"
            await self._log_error(error_msg)
            return error_msg
        finally:
            self.state = AgentState.IDLE
    
    async def _store_thought(self, thought: AgentThought) -> None:
        """Store thought in memory."""
        try:
            thought_text = f"""
Agent: {self.name}
Observation: {thought.observation}
Thought: {thought.thought}
Action: {thought.action}
Action Input: {thought.action_input}
Result: {thought.result}
"""
            await self.memory.store_text(
                text=thought_text,
                metadata={
                    "agent": self.name,
                    "type": "thought",
                    "timestamp": thought.timestamp.isoformat(),
                    "action": thought.action
                }
            )
        except Exception as e:
            print(f"Failed to store thought: {e}")
    
    async def _log_error(self, error: str) -> None:
        """Log error to memory."""
        try:
            await self.memory.store_text(
                text=f"Agent {self.name} error: {error}",
                metadata={
                    "agent": self.name,
                    "type": "error",
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            print(f"Failed to log error: {e}")
    
    async def send_message(self, recipient: str, content: str, message_type: str = "text") -> None:
        """Send message to another agent."""
        message = AgentMessage(
            sender=self.name,
            recipient=recipient,
            content=content,
            message_type=message_type
        )
        
        if self.message_bus:
            await self.message_bus.send_message(message)
    
    async def receive_message(self) -> Optional[AgentMessage]:
        """Receive message from queue."""
        try:
            message = await asyncio.wait_for(self.message_queue.get(), timeout=0.1)
            return message
        except asyncio.TimeoutError:
            return None
    
    async def get_relevant_context(self, query: str, limit: int = 5) -> List[str]:
        """Get relevant context from memory."""
        try:
            results = await self.memory.search(query, limit=limit)
            return [result.text for result in results]
        except Exception as e:
            print(f"Failed to get context: {e}")
            return []
    
    def add_capability(self, capability: str) -> None:
        """Add a capability to the agent."""
        if capability not in self.capabilities:
            self.capabilities.append(capability)
    
    def add_tool(self, name: str, tool: Any) -> None:
        """Add a tool to the agent."""
        self.tools[name] = tool
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "current_task": self.current_task,
            "capabilities": self.capabilities,
            "thoughts_count": len(self.thoughts),
            "last_thought": self.thoughts[-1].__dict__ if self.thoughts else None
        }
    
    async def reset(self) -> None:
        """Reset agent state."""
        self.state = AgentState.IDLE
        self.current_task = None
        self.thoughts.clear()
        
        # Clear message queue
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
    
    def set_message_bus(self, message_bus: Any) -> None:
        """Set message bus for communication."""
        self.message_bus = message_bus
    
    async def stream_thoughts(self) -> AsyncGenerator[AgentThought, None]:
        """Stream thoughts as they are generated."""
        last_count = 0
        while self.state != AgentState.IDLE:
            if len(self.thoughts) > last_count:
                for thought in self.thoughts[last_count:]:
                    yield thought
                last_count = len(self.thoughts)
            await asyncio.sleep(0.1)