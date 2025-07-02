"""
Planner Agent - Breaks down complex tasks into actionable steps.
"""

import json
from typing import Dict, List, Any
from dataclasses import dataclass

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent, AgentThought
from llm_engine import FunctionSchema


@dataclass
class TaskStep:
    """Individual step in a task plan."""
    id: str
    description: str
    agent: str
    dependencies: List[str]
    estimated_effort: str
    success_criteria: str
    status: str = "pending"  # pending, in_progress, completed, failed


@dataclass
class TaskPlan:
    """Complete task plan."""
    task_id: str
    description: str
    steps: List[TaskStep]
    estimated_total_effort: str
    created_at: str


class PlannerAgent(BaseAgent):
    """Agent responsible for task planning and decomposition."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role_description = """
You are a senior project manager and architect responsible for breaking down complex software development tasks into actionable steps. You excel at:
- Analyzing requirements and identifying dependencies
- Creating detailed, executable plans
- Estimating effort and identifying risks
- Coordinating between different specialists
"""
        self.add_capability("task_decomposition")
        self.add_capability("project_planning")
        self.add_capability("dependency_analysis")
    
    def _setup_functions(self) -> None:
        """Setup planner-specific functions."""
        
        # Create task plan function
        create_plan_schema = FunctionSchema(
            name="create_task_plan",
            description="Create a detailed task plan with steps and dependencies",
            parameters={
                "task_description": {
                    "type": "string",
                    "description": "Description of the main task"
                },
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "description": {"type": "string"},
                            "agent": {"type": "string"},
                            "dependencies": {"type": "array", "items": {"type": "string"}},
                            "estimated_effort": {"type": "string"},
                            "success_criteria": {"type": "string"}
                        }
                    }
                },
                "estimated_total_effort": {"type": "string"}
            },
            required=["task_description", "steps", "estimated_total_effort"]
        )
        
        self.function_caller.register_function(
            self._create_task_plan,
            create_plan_schema
        )
        
        # Analyze dependencies function
        analyze_deps_schema = FunctionSchema(
            name="analyze_dependencies",
            description="Analyze dependencies between task steps",
            parameters={
                "steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of task steps to analyze"
                }
            },
            required=["steps"]
        )
        
        self.function_caller.register_function(
            self._analyze_dependencies,
            analyze_deps_schema
        )
    
    async def _think(self, observation: str) -> AgentThought:
        """Generate planning thoughts."""
        
        # Get relevant context from memory
        context = await self.get_relevant_context(observation)
        context_str = "\n".join(context) if context else "No relevant context found."
        
        # Build planning prompt
        prompt = self.prompt_builder.build_prompt(
            "task_planning",
            task=observation,
            context=context_str,
            constraints="Must be executable by available agents: CoderAgent, TerminalAgent, DebuggerAgent, GitAgent"
        )
        
        # Get LLM response
        response = await self.llm.generate(prompt)
        
        # Parse the response to extract thought components
        lines = response.content.strip().split('\n')
        
        thought_text = ""
        action = "create_task_plan"
        action_input = {}
        
        # Try to extract structured information
        for line in lines:
            if line.startswith("Thought:"):
                thought_text = line.replace("Thought:", "").strip()
            elif line.startswith("Action:"):
                action = line.replace("Action:", "").strip()
        
        # If no structured thought found, use the whole response
        if not thought_text:
            thought_text = response.content
        
        return AgentThought(
            observation=observation,
            thought=thought_text,
            action=action,
            action_input=action_input
        )
    
    async def _act(self, thought: AgentThought) -> str:
        """Execute planning action."""
        
        if thought.action == "create_task_plan":
            return await self._generate_detailed_plan(thought.observation)
        elif thought.action == "analyze_dependencies":
            return await self._perform_dependency_analysis(thought.observation)
        else:
            # Use function calling for other actions
            function_calls = self.function_caller.parse_function_calls(thought.thought)
            if function_calls:
                results = await self.function_caller.execute_function_calls(function_calls)
                return self.function_caller.format_function_results(results)
            else:
                return f"Completed planning analysis: {thought.thought}"
    
    async def _generate_detailed_plan(self, task: str) -> str:
        """Generate a detailed task plan."""
        
        planning_prompt = f"""
Analyze this software development task and create a detailed execution plan:

TASK: {task}

Create a plan with the following structure:
1. Break down into 5-10 actionable steps
2. Assign each step to the most appropriate agent:
   - CoderAgent: Code generation, modification, refactoring
   - TerminalAgent: Command execution, testing, building
   - DebuggerAgent: Error analysis and fixing
   - GitAgent: Version control operations
   - SearchAgent: Code analysis and search

3. Identify dependencies between steps
4. Estimate effort (Small/Medium/Large)
5. Define clear success criteria

Format as JSON:
{{
  "task_description": "...",
  "steps": [
    {{
      "id": "step_1",
      "description": "...",
      "agent": "CoderAgent",
      "dependencies": [],
      "estimated_effort": "Medium",
      "success_criteria": "..."
    }}
  ],
  "estimated_total_effort": "Large"
}}
"""
        
        response = await self.llm.generate(planning_prompt)
        
        try:
            # Try to parse JSON from response
            plan_data = json.loads(response.content)
            plan = TaskPlan(
                task_id=f"task_{len(self.thoughts)}",
                description=plan_data["task_description"],
                steps=[TaskStep(**step) for step in plan_data["steps"]],
                estimated_total_effort=plan_data["estimated_total_effort"],
                created_at=str(self.thoughts[-1].timestamp) if self.thoughts else ""
            )
            
            # Store plan in memory
            await self.memory.store_text(
                text=json.dumps(plan_data, indent=2),
                metadata={
                    "type": "task_plan",
                    "agent": self.name,
                    "task_id": plan.task_id
                }
            )
            
            return f"Created detailed plan with {len(plan.steps)} steps:\n{json.dumps(plan_data, indent=2)}"
            
        except json.JSONDecodeError:
            # Fallback to text-based plan
            return f"Generated plan (text format):\n{response.content}"
    
    async def _perform_dependency_analysis(self, context: str) -> str:
        """Analyze dependencies between tasks."""
        
        analysis_prompt = f"""
Analyze the dependencies in this development context:

{context}

Identify:
1. Which tasks must be completed before others can start
2. Which tasks can be done in parallel
3. Critical path items that could block progress
4. Potential risks or bottlenecks

Provide a clear dependency analysis.
"""
        
        response = await self.llm.generate(analysis_prompt)
        return response.content
    
    async def _create_task_plan(self, task_description: str, steps: List[Dict], estimated_total_effort: str) -> str:
        """Function to create a task plan."""
        
        plan = TaskPlan(
            task_id=f"plan_{len(self.thoughts)}",
            description=task_description,
            steps=[TaskStep(**step) for step in steps],
            estimated_total_effort=estimated_total_effort,
            created_at=str(self.thoughts[-1].timestamp) if self.thoughts else ""
        )
        
        # Store in memory
        await self.memory.store_text(
            text=json.dumps({
                "task_description": task_description,
                "steps": steps,
                "estimated_total_effort": estimated_total_effort
            }, indent=2),
            metadata={
                "type": "task_plan",
                "agent": self.name,
                "task_id": plan.task_id
            }
        )
        
        return f"Created task plan '{plan.task_id}' with {len(plan.steps)} steps"
    
    async def _analyze_dependencies(self, steps: List[str]) -> str:
        """Function to analyze step dependencies."""
        
        analysis_prompt = f"""
Analyze dependencies between these development steps:

{chr(10).join(f"- {step}" for step in steps)}

For each step, identify:
1. Prerequisites (what must be done first)
2. Parallel opportunities (what can be done simultaneously)
3. Blocking potential (what this step blocks)

Provide dependency analysis.
"""
        
        response = await self.llm.generate(analysis_prompt)
        return response.content
    
    async def get_plan_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a specific plan."""
        
        # Search for plan in memory
        results = await self.memory.search(f"task_id:{task_id}", limit=1)
        
        if results:
            try:
                plan_data = json.loads(results[0].text)
                return {
                    "task_id": task_id,
                    "found": True,
                    "plan": plan_data
                }
            except json.JSONDecodeError:
                pass
        
        return {
            "task_id": task_id,
            "found": False,
            "plan": None
        }