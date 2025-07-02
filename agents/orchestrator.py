"""
Agent Orchestrator - Coordinates multi-agent workflows.
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from agents.base_agent import BaseAgent, AgentMessage, AgentState
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory import VectorMemory


@dataclass
class TaskExecution:
    """Represents a task execution workflow."""
    task_id: str
    description: str
    assigned_agents: List[str]
    current_step: int
    total_steps: int
    status: str  # pending, running, completed, failed
    results: Dict[str, Any]
    start_time: datetime
    end_time: Optional[datetime] = None


class MessageBus:
    """Message bus for agent communication."""
    
    def __init__(self):
        self.subscribers: Dict[str, List[BaseAgent]] = {}
        self.message_history: List[AgentMessage] = []
    
    def subscribe(self, agent: BaseAgent, topics: List[str] = None):
        """Subscribe agent to message topics."""
        topics = topics or ["all"]
        
        for topic in topics:
            if topic not in self.subscribers:
                self.subscribers[topic] = []
            self.subscribers[topic].append(agent)
    
    async def send_message(self, message: AgentMessage):
        """Send message to subscribers."""
        self.message_history.append(message)
        
        # Send to specific recipient
        if message.recipient != "all":
            for topic_agents in self.subscribers.values():
                for agent in topic_agents:
                    if agent.name == message.recipient:
                        await agent.message_queue.put(message)
                        return
        
        # Broadcast to all subscribers
        for topic_agents in self.subscribers.values():
            for agent in topic_agents:
                if agent.name != message.sender:  # Don't send to sender
                    await agent.message_queue.put(message)
    
    def get_message_history(self, limit: int = 100) -> List[AgentMessage]:
        """Get recent message history."""
        return self.message_history[-limit:]


class AgentOrchestrator:
    """Orchestrates multi-agent workflows and task execution."""
    
    def __init__(self, agents: Dict[str, BaseAgent], memory: VectorMemory):
        self.agents = agents
        self.memory = memory
        self.message_bus = MessageBus()
        
        # Setup message bus for all agents
        for agent in agents.values():
            agent.set_message_bus(self.message_bus)
            self.message_bus.subscribe(agent)
        
        # Task tracking
        self.active_tasks: Dict[str, TaskExecution] = {}
        self.task_counter = 0
    
    async def process_task(self, task_description: str, context: Dict[str, Any] = None) -> str:
        """Process a complex task using multiple agents."""
        
        self.task_counter += 1
        task_id = f"task_{self.task_counter}"
        
        context = context or {}
        
        try:
            # Step 1: Planning
            plan_result = await self._create_execution_plan(task_description, context)
            
            if not plan_result:
                return "Failed to create execution plan"
            
            # Step 2: Execute plan
            execution_result = await self._execute_plan(task_id, task_description, plan_result, context)
            
            return execution_result
            
        except Exception as e:
            return f"Error processing task: {str(e)}"
    
    async def _create_execution_plan(self, task_description: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create an execution plan using the PlannerAgent."""
        
        if "planner" not in self.agents:
            # Simple fallback plan
            return {
                "steps": [
                    {"agent": "coder", "action": "analyze_and_implement", "description": task_description}
                ]
            }
        
        planner = self.agents["planner"]
        
        # Create planning context
        planning_context = {
            "available_agents": list(self.agents.keys()),
            "agent_capabilities": {
                name: agent.capabilities for name, agent in self.agents.items()
            },
            **context
        }
        
        # Get plan from planner
        plan_prompt = f"""
Create an execution plan for this task:

TASK: {task_description}

AVAILABLE AGENTS: {', '.join(self.agents.keys())}

CONTEXT: {json.dumps(planning_context, indent=2)}

Create a step-by-step plan that assigns specific actions to the most appropriate agents.
"""
        
        try:
            plan_result = await planner.process_task(plan_prompt, planning_context)
            
            # Try to parse structured plan from result
            plan = self._parse_plan_from_result(plan_result)
            
            return plan
            
        except Exception as e:
            print(f"Planning failed: {e}")
            return None
    
    def _parse_plan_from_result(self, plan_result: str) -> Dict[str, Any]:
        """Parse execution plan from planner result."""
        
        # Try to extract JSON from the result
        import re
        
        json_pattern = r'```json\s*(\{.*?\})\s*```'
        matches = re.findall(json_pattern, plan_result, re.DOTALL)
        
        if matches:
            try:
                return json.loads(matches[0])
            except json.JSONDecodeError:
                pass
        
        # Fallback: create simple plan based on task content
        task_lower = plan_result.lower()
        
        steps = []
        
        # Determine which agents to use based on keywords
        if any(word in task_lower for word in ["code", "implement", "write", "create", "develop"]):
            steps.append({
                "agent": "coder",
                "action": "implement",
                "description": "Implement the requested functionality"
            })
        
        if any(word in task_lower for word in ["test", "run", "execute", "build", "install"]):
            steps.append({
                "agent": "terminal",
                "action": "execute",
                "description": "Run tests and build commands"
            })
        
        if any(word in task_lower for word in ["git", "commit", "push", "version"]):
            steps.append({
                "agent": "git",
                "action": "version_control",
                "description": "Handle version control operations"
            })
        
        if any(word in task_lower for word in ["debug", "fix", "error", "bug"]):
            steps.append({
                "agent": "debugger",
                "action": "debug",
                "description": "Debug and fix issues"
            })
        
        # Default to coder if no specific actions identified
        if not steps:
            steps.append({
                "agent": "coder",
                "action": "analyze",
                "description": plan_result
            })
        
        return {"steps": steps}
    
    async def _execute_plan(
        self,
        task_id: str,
        task_description: str,
        plan: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Execute the planned steps."""
        
        steps = plan.get("steps", [])
        
        if not steps:
            return "No execution steps found in plan"
        
        # Create task execution record
        execution = TaskExecution(
            task_id=task_id,
            description=task_description,
            assigned_agents=[step.get("agent", "") for step in steps],
            current_step=0,
            total_steps=len(steps),
            status="running",
            results={},
            start_time=datetime.now()
        )
        
        self.active_tasks[task_id] = execution
        
        results = []
        
        try:
            for i, step in enumerate(steps):
                execution.current_step = i + 1
                
                agent_name = step.get("agent", "")
                action = step.get("action", "")
                description = step.get("description", "")
                
                if agent_name not in self.agents:
                    result = f"Agent '{agent_name}' not available"
                    results.append(f"Step {i+1}: {result}")
                    continue
                
                agent = self.agents[agent_name]
                
                # Prepare step context
                step_context = {
                    "task_id": task_id,
                    "step_number": i + 1,
                    "total_steps": len(steps),
                    "action": action,
                    "previous_results": results,
                    **context
                }
                
                # Execute step
                try:
                    step_result = await agent.process_task(description, step_context)
                    execution.results[f"step_{i+1}"] = step_result
                    results.append(f"Step {i+1} ({agent_name}): {step_result}")
                    
                    # Store step result in memory
                    await self.memory.store_text(
                        text=f"Task {task_id} Step {i+1} Result: {step_result}",
                        metadata={
                            "type": "step_result",
                            "task_id": task_id,
                            "step_number": i + 1,
                            "agent": agent_name,
                            "action": action
                        }
                    )
                    
                except Exception as e:
                    error_result = f"Error in step {i+1}: {str(e)}"
                    results.append(error_result)
                    execution.results[f"step_{i+1}_error"] = str(e)
            
            execution.status = "completed"
            execution.end_time = datetime.now()
            
            # Create final summary
            summary = self._create_execution_summary(execution, results)
            
            # Store final result in memory
            await self.memory.store_text(
                text=f"Task {task_id} completed: {summary}",
                metadata={
                    "type": "task_completion",
                    "task_id": task_id,
                    "description": task_description,
                    "total_steps": len(steps),
                    "status": execution.status
                }
            )
            
            return summary
            
        except Exception as e:
            execution.status = "failed"
            execution.end_time = datetime.now()
            error_msg = f"Task execution failed: {str(e)}"
            
            # Store error in memory
            await self.memory.store_text(
                text=f"Task {task_id} failed: {error_msg}",
                metadata={
                    "type": "task_error",
                    "task_id": task_id,
                    "description": task_description,
                    "error": str(e)
                }
            )
            
            return error_msg
        
        finally:
            # Clean up completed task
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
    
    def _create_execution_summary(self, execution: TaskExecution, results: List[str]) -> str:
        """Create a summary of task execution."""
        
        duration = (execution.end_time - execution.start_time).total_seconds()
        
        summary_parts = [
            f"✅ Task '{execution.description}' completed successfully",
            f"📊 Execution Summary:",
            f"  - Task ID: {execution.task_id}",
            f"  - Steps: {execution.total_steps}",
            f"  - Duration: {duration:.2f} seconds",
            f"  - Agents used: {', '.join(set(execution.assigned_agents))}",
            "",
            "📝 Step Results:"
        ]
        
        for i, result in enumerate(results, 1):
            summary_parts.append(f"  {i}. {result}")
        
        return "\n".join(summary_parts)
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task."""
        
        if task_id in self.active_tasks:
            execution = self.active_tasks[task_id]
            return {
                "task_id": task_id,
                "description": execution.description,
                "status": execution.status,
                "current_step": execution.current_step,
                "total_steps": execution.total_steps,
                "progress": execution.current_step / execution.total_steps,
                "assigned_agents": execution.assigned_agents,
                "start_time": execution.start_time.isoformat(),
                "results": execution.results
            }
        
        return None
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents."""
        
        status = {}
        
        for name, agent in self.agents.items():
            agent_status = agent.get_status()
            status[name] = {
                "state": agent_status["state"],
                "current_task": agent_status.get("current_task"),
                "capabilities": agent_status.get("capabilities", []),
                "thoughts_count": agent_status.get("thoughts_count", 0)
            }
        
        return status
    
    async def broadcast_message(self, sender: str, content: str, message_type: str = "info"):
        """Broadcast a message to all agents."""
        
        message = AgentMessage(
            sender=sender,
            recipient="all",
            content=content,
            message_type=message_type
        )
        
        await self.message_bus.send_message(message)
    
    async def send_direct_message(self, sender: str, recipient: str, content: str):
        """Send a direct message between agents."""
        
        message = AgentMessage(
            sender=sender,
            recipient=recipient,
            content=content,
            message_type="direct"
        )
        
        await self.message_bus.send_message(message)
    
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get list of currently active tasks."""
        
        return [
            {
                "task_id": execution.task_id,
                "description": execution.description,
                "status": execution.status,
                "progress": execution.current_step / execution.total_steps,
                "start_time": execution.start_time.isoformat()
            }
            for execution in self.active_tasks.values()
        ]