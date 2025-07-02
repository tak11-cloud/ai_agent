"""
Debugger Agent - Analyzes errors and implements fixes.
"""

import re
import json
from typing import Dict, List, Any, Optional

from agents.base_agent import BaseAgent, AgentThought
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_engine import FunctionSchema


class DebuggerAgent(BaseAgent):
    """Agent responsible for debugging and error analysis."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role_description = """
You are an expert debugger and error analyst with deep knowledge of common programming issues. You excel at:
- Analyzing stack traces and error messages
- Identifying root causes of bugs
- Suggesting specific fixes and improvements
- Understanding code flow and logic errors
- Providing preventive measures
"""
        self.add_capability("error_analysis")
        self.add_capability("bug_fixing")
        self.add_capability("code_debugging")
        self.add_capability("performance_analysis")
    
    def _setup_functions(self) -> None:
        """Setup debugger-specific functions."""
        
        # Analyze error function
        analyze_error_schema = FunctionSchema(
            name="analyze_error",
            description="Analyze an error message and stack trace",
            parameters={
                "error_message": {
                    "type": "string",
                    "description": "The error message"
                },
                "stack_trace": {
                    "type": "string",
                    "description": "The stack trace or traceback"
                },
                "code_context": {
                    "type": "string",
                    "description": "Relevant code context"
                }
            },
            required=["error_message"]
        )
        
        self.function_caller.register_function(
            self._analyze_error,
            analyze_error_schema
        )
        
        # Suggest fix function
        suggest_fix_schema = FunctionSchema(
            name="suggest_fix",
            description="Suggest a fix for a specific bug",
            parameters={
                "bug_description": {
                    "type": "string",
                    "description": "Description of the bug"
                },
                "code_snippet": {
                    "type": "string",
                    "description": "Code snippet with the bug"
                },
                "error_details": {
                    "type": "string",
                    "description": "Error details and context"
                }
            },
            required=["bug_description", "code_snippet"]
        )
        
        self.function_caller.register_function(
            self._suggest_fix,
            suggest_fix_schema
        )
    
    async def _think(self, observation: str) -> AgentThought:
        """Generate debugging thoughts."""
        
        # Get relevant context from memory
        context = await self.get_relevant_context(observation)
        context_str = "\n".join(context) if context else "No relevant context found."
        
        # Analyze the observation to determine debugging approach
        debug_type = self._analyze_debug_type(observation)
        
        # Build debugging prompt
        prompt = f"""
You are an expert debugger. Analyze this issue and provide debugging insights:

ISSUE: {observation}

CONTEXT: {context_str}

DEBUG TYPE: {debug_type}

Analyze the issue and determine:
1. What type of error or problem is this?
2. What are the likely root causes?
3. What debugging steps should be taken?
4. What information is needed to solve this?

Provide your analysis and recommended action.
"""
        
        # Get LLM response
        response = await self.llm.generate(prompt)
        
        # Parse response for action
        action = self._extract_debug_action(response.content, observation)
        action_input = self._extract_debug_input(response.content, observation)
        
        return AgentThought(
            observation=observation,
            thought=response.content,
            action=action,
            action_input=action_input
        )
    
    async def _act(self, thought: AgentThought) -> str:
        """Execute debugging action."""
        
        if thought.action == "analyze_error":
            return await self._handle_error_analysis(thought)
        elif thought.action == "suggest_fix":
            return await self._handle_fix_suggestion(thought)
        elif thought.action == "debug_code":
            return await self._handle_code_debugging(thought)
        else:
            # Use function calling
            function_calls = self.function_caller.parse_function_calls(thought.thought)
            if function_calls:
                results = await self.function_caller.execute_function_calls(function_calls)
                return self.function_caller.format_function_results(results)
            else:
                return f"Analyzed issue: {thought.thought}"
    
    def _analyze_debug_type(self, observation: str) -> str:
        """Analyze what type of debugging is needed."""
        
        observation_lower = observation.lower()
        
        if any(word in observation_lower for word in ["error", "exception", "traceback", "stack trace"]):
            return "error_analysis"
        elif any(word in observation_lower for word in ["bug", "fix", "broken", "not working"]):
            return "bug_fixing"
        elif any(word in observation_lower for word in ["slow", "performance", "memory", "cpu"]):
            return "performance_analysis"
        elif any(word in observation_lower for word in ["test", "failing", "assertion"]):
            return "test_debugging"
        else:
            return "general_debugging"
    
    def _extract_debug_action(self, response: str, observation: str) -> str:
        """Extract the intended debugging action."""
        
        response_lower = response.lower()
        observation_lower = observation.lower()
        
        if "analyze" in response_lower and ("error" in response_lower or "error" in observation_lower):
            return "analyze_error"
        elif "suggest" in response_lower or "fix" in response_lower:
            return "suggest_fix"
        elif "debug" in response_lower:
            return "debug_code"
        else:
            return "analyze_error"  # Default
    
    def _extract_debug_input(self, response: str, observation: str) -> Dict[str, Any]:
        """Extract debugging input parameters."""
        
        # Try to extract error messages and stack traces
        error_patterns = [
            r'Error:\s*(.+)',
            r'Exception:\s*(.+)',
            r'Traceback.*?:\s*(.+)',
        ]
        
        error_message = ""
        for pattern in error_patterns:
            matches = re.findall(pattern, observation, re.IGNORECASE | re.MULTILINE)
            if matches:
                error_message = matches[0]
                break
        
        # Extract stack trace
        stack_trace = ""
        if "traceback" in observation.lower() or "stack trace" in observation.lower():
            lines = observation.split('\n')
            in_trace = False
            trace_lines = []
            
            for line in lines:
                if any(word in line.lower() for word in ["traceback", "stack trace", "at line"]):
                    in_trace = True
                
                if in_trace:
                    trace_lines.append(line)
                
                if in_trace and line.strip() == "":
                    break
            
            stack_trace = '\n'.join(trace_lines)
        
        return {
            "error_message": error_message or observation,
            "stack_trace": stack_trace,
            "code_context": response,
            "bug_description": observation,
            "code_snippet": "",
            "error_details": observation
        }
    
    async def _handle_error_analysis(self, thought: AgentThought) -> str:
        """Handle error analysis."""
        
        error_message = thought.action_input.get("error_message", "")
        stack_trace = thought.action_input.get("stack_trace", "")
        code_context = thought.action_input.get("code_context", "")
        
        analysis_prompt = f"""
Analyze this error in detail:

ERROR MESSAGE: {error_message}

STACK TRACE: {stack_trace}

CODE CONTEXT: {code_context}

Provide a comprehensive analysis including:
1. Error type and category
2. Root cause analysis
3. Affected components
4. Potential impact
5. Recommended fix strategy
6. Prevention measures

Analysis:
"""
        
        response = await self.llm.generate(analysis_prompt)
        
        # Store analysis in memory
        await self.memory.store_text(
            text=f"Error analysis: {error_message}\n\nAnalysis: {response.content}",
            metadata={
                "type": "error_analysis",
                "agent": self.name,
                "error_type": self._classify_error_type(error_message)
            }
        )
        
        return response.content
    
    async def _handle_fix_suggestion(self, thought: AgentThought) -> str:
        """Handle fix suggestion."""
        
        bug_description = thought.action_input.get("bug_description", "")
        code_snippet = thought.action_input.get("code_snippet", "")
        error_details = thought.action_input.get("error_details", "")
        
        fix_prompt = f"""
Suggest a specific fix for this bug:

BUG DESCRIPTION: {bug_description}

CODE SNIPPET: {code_snippet}

ERROR DETAILS: {error_details}

Provide:
1. Specific code changes needed
2. Explanation of why the fix works
3. Alternative solutions if applicable
4. Testing recommendations
5. Potential side effects to consider

Fix suggestion:
"""
        
        response = await self.llm.generate(fix_prompt)
        
        # Store fix suggestion in memory
        await self.memory.store_text(
            text=f"Fix suggestion for: {bug_description}\n\nSuggestion: {response.content}",
            metadata={
                "type": "fix_suggestion",
                "agent": self.name,
                "bug_type": self._classify_bug_type(bug_description)
            }
        )
        
        return response.content
    
    async def _handle_code_debugging(self, thought: AgentThought) -> str:
        """Handle general code debugging."""
        
        debug_prompt = f"""
Debug this code issue:

ISSUE: {thought.observation}

ANALYSIS: {thought.thought}

Provide debugging steps:
1. What to check first
2. How to reproduce the issue
3. Debugging tools to use
4. Common causes for this type of issue
5. Step-by-step debugging process

Debugging guide:
"""
        
        response = await self.llm.generate(debug_prompt)
        
        # Store debugging guide in memory
        await self.memory.store_text(
            text=f"Debugging guide: {thought.observation}\n\nGuide: {response.content}",
            metadata={
                "type": "debugging_guide",
                "agent": self.name
            }
        )
        
        return response.content
    
    def _classify_error_type(self, error_message: str) -> str:
        """Classify the type of error."""
        
        error_lower = error_message.lower()
        
        if any(word in error_lower for word in ["syntax", "invalid syntax"]):
            return "syntax_error"
        elif any(word in error_lower for word in ["name", "not defined", "undefined"]):
            return "name_error"
        elif any(word in error_lower for word in ["type", "wrong type", "cannot convert"]):
            return "type_error"
        elif any(word in error_lower for word in ["index", "out of range", "bounds"]):
            return "index_error"
        elif any(word in error_lower for word in ["key", "not found", "missing"]):
            return "key_error"
        elif any(word in error_lower for word in ["attribute", "has no attribute"]):
            return "attribute_error"
        elif any(word in error_lower for word in ["import", "module", "cannot import"]):
            return "import_error"
        elif any(word in error_lower for word in ["connection", "network", "timeout"]):
            return "network_error"
        elif any(word in error_lower for word in ["file", "not found", "permission"]):
            return "file_error"
        else:
            return "unknown_error"
    
    def _classify_bug_type(self, bug_description: str) -> str:
        """Classify the type of bug."""
        
        bug_lower = bug_description.lower()
        
        if any(word in bug_lower for word in ["logic", "wrong result", "incorrect"]):
            return "logic_bug"
        elif any(word in bug_lower for word in ["performance", "slow", "memory"]):
            return "performance_bug"
        elif any(word in bug_lower for word in ["ui", "interface", "display"]):
            return "ui_bug"
        elif any(word in bug_lower for word in ["security", "vulnerability", "exploit"]):
            return "security_bug"
        elif any(word in bug_lower for word in ["data", "database", "corruption"]):
            return "data_bug"
        elif any(word in bug_lower for word in ["race", "concurrency", "thread"]):
            return "concurrency_bug"
        else:
            return "general_bug"
    
    async def _analyze_error(
        self,
        error_message: str,
        stack_trace: str = "",
        code_context: str = ""
    ) -> str:
        """Function to analyze error."""
        return await self._handle_error_analysis(AgentThought(
            observation=error_message,
            thought="Analyzing error",
            action="analyze_error",
            action_input={
                "error_message": error_message,
                "stack_trace": stack_trace,
                "code_context": code_context
            }
        ))
    
    async def _suggest_fix(
        self,
        bug_description: str,
        code_snippet: str,
        error_details: str = ""
    ) -> str:
        """Function to suggest fix."""
        return await self._handle_fix_suggestion(AgentThought(
            observation=bug_description,
            thought="Suggesting fix",
            action="suggest_fix",
            action_input={
                "bug_description": bug_description,
                "code_snippet": code_snippet,
                "error_details": error_details
            }
        ))