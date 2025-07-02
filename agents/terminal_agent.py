"""
Terminal Agent - Executes commands in sandboxed environment.
"""

import json
from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentThought
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_engine import FunctionSchema
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from executor import TerminalRunner


class TerminalAgent(BaseAgent):
    """Agent responsible for command execution."""
    
    def __init__(self, terminal_runner: TerminalRunner, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.terminal_runner = terminal_runner
        self.role_description = """
You are a system administrator and command-line expert responsible for executing commands safely. You excel at:
- Running development tools and build systems
- Managing files and directories
- Installing packages and dependencies
- Running tests and scripts
- Monitoring system resources
"""
        self.add_capability("command_execution")
        self.add_capability("file_operations")
        self.add_capability("package_management")
        self.add_capability("process_management")
    
    def _setup_functions(self) -> None:
        """Setup terminal-specific functions."""
        
        # Execute command function
        execute_schema = FunctionSchema(
            name="execute_command",
            description="Execute a shell command",
            parameters={
                "command": {
                    "type": "string",
                    "description": "The command to execute"
                },
                "working_directory": {
                    "type": "string",
                    "description": "Working directory for the command"
                },
                "timeout": {
                    "type": "number",
                    "description": "Timeout in seconds"
                },
                "capture_output": {
                    "type": "boolean",
                    "description": "Whether to capture command output"
                }
            },
            required=["command"]
        )
        
        self.function_caller.register_function(
            self._execute_command,
            execute_schema
        )
        
        # Execute script function
        execute_script_schema = FunctionSchema(
            name="execute_script",
            description="Execute a script",
            parameters={
                "script_content": {
                    "type": "string",
                    "description": "Content of the script to execute"
                },
                "script_type": {
                    "type": "string",
                    "description": "Type of script (bash, python, javascript)"
                },
                "timeout": {
                    "type": "number",
                    "description": "Timeout in seconds"
                }
            },
            required=["script_content", "script_type"]
        )
        
        self.function_caller.register_function(
            self._execute_script,
            execute_script_schema
        )
    
    async def _think(self, observation: str) -> AgentThought:
        """Generate terminal execution thoughts."""
        
        # Get relevant context from memory
        context = await self.get_relevant_context(observation)
        context_str = "\n".join(context) if context else "No relevant context found."
        
        # Build terminal prompt
        prompt = f"""
You are a terminal execution expert. Analyze this request and determine what commands to run:

REQUEST: {observation}

CONTEXT: {context_str}

Consider:
1. What commands are needed to fulfill this request?
2. Are there any dependencies or prerequisites?
3. What is the safest way to execute this?
4. Should commands be run in sequence or can some be parallel?

Provide your analysis and the specific command(s) to execute.
Format your response as:

Thought: [Your analysis]
Action: [execute_command or execute_script]
Command: [The specific command or script]
"""
        
        # Get LLM response
        response = await self.llm.generate(prompt)
        
        # Parse response
        lines = response.content.strip().split('\n')
        
        thought_text = ""
        action = "execute_command"
        command = ""
        
        for line in lines:
            if line.startswith("Thought:"):
                thought_text = line.replace("Thought:", "").strip()
            elif line.startswith("Action:"):
                action = line.replace("Action:", "").strip()
            elif line.startswith("Command:"):
                command = line.replace("Command:", "").strip()
        
        # If no structured response, extract command from content
        if not command:
            # Try to find command-like patterns
            import re
            cmd_patterns = [
                r'`([^`]+)`',  # Commands in backticks
                r'```(?:bash|sh)?\n([^```]+)\n```',  # Code blocks
                r'run:\s*(.+)',  # "run: command"
                r'execute:\s*(.+)',  # "execute: command"
            ]
            
            for pattern in cmd_patterns:
                matches = re.findall(pattern, response.content, re.MULTILINE | re.DOTALL)
                if matches:
                    command = matches[0].strip()
                    break
        
        if not thought_text:
            thought_text = response.content
        
        return AgentThought(
            observation=observation,
            thought=thought_text,
            action=action,
            action_input={"command": command}
        )
    
    async def _act(self, thought: AgentThought) -> str:
        """Execute terminal action."""
        
        if thought.action == "execute_command":
            command = thought.action_input.get("command", "")
            if not command:
                return "No command specified"
            
            return await self._run_command(command)
        
        elif thought.action == "execute_script":
            script_content = thought.action_input.get("script_content", "")
            script_type = thought.action_input.get("script_type", "bash")
            
            if not script_content:
                return "No script content specified"
            
            return await self._run_script(script_content, script_type)
        
        else:
            # Use function calling
            function_calls = self.function_caller.parse_function_calls(thought.thought)
            if function_calls:
                results = await self.function_caller.execute_function_calls(function_calls)
                return self.function_caller.format_function_results(results)
            else:
                return f"Analyzed request: {thought.thought}"
    
    async def _run_command(
        self,
        command: str,
        working_directory: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> str:
        """Run a single command."""
        
        try:
            result = await self.terminal_runner.execute_command(
                command=command,
                working_directory=working_directory,
                timeout=timeout or 30,
                capture_output=True
            )
            
            # Format result
            output_parts = []
            
            if result.exit_code == 0:
                output_parts.append(f"✅ Command executed successfully")
            else:
                output_parts.append(f"❌ Command failed with exit code {result.exit_code}")
            
            output_parts.append(f"Command: {result.command}")
            output_parts.append(f"Working Directory: {result.working_directory}")
            output_parts.append(f"Execution Time: {result.execution_time:.2f}s")
            
            if result.stdout:
                output_parts.append(f"STDOUT:\n{result.stdout}")
            
            if result.stderr:
                output_parts.append(f"STDERR:\n{result.stderr}")
            
            if result.timeout:
                output_parts.append("⚠️ Command timed out")
            
            if result.killed:
                output_parts.append("⚠️ Command was forcefully terminated")
            
            # Store execution in memory
            await self.memory.store_text(
                text=f"Executed command: {command}\nResult: {result.stdout}\nError: {result.stderr}",
                metadata={
                    "type": "command_execution",
                    "agent": self.name,
                    "command": command,
                    "exit_code": result.exit_code,
                    "execution_time": result.execution_time
                }
            )
            
            return "\n".join(output_parts)
            
        except Exception as e:
            error_msg = f"Failed to execute command '{command}': {str(e)}"
            
            # Store error in memory
            await self.memory.store_text(
                text=f"Command execution error: {command}\nError: {error_msg}",
                metadata={
                    "type": "command_error",
                    "agent": self.name,
                    "command": command
                }
            )
            
            return error_msg
    
    async def _run_script(self, script_content: str, script_type: str) -> str:
        """Run a script."""
        
        try:
            result = await self.terminal_runner.execute_script(
                script_content=script_content,
                script_type=script_type,
                timeout=60
            )
            
            # Format result
            output_parts = []
            
            if result.exit_code == 0:
                output_parts.append(f"✅ Script executed successfully")
            else:
                output_parts.append(f"❌ Script failed with exit code {result.exit_code}")
            
            output_parts.append(f"Script Type: {script_type}")
            output_parts.append(f"Execution Time: {result.execution_time:.2f}s")
            
            if result.stdout:
                output_parts.append(f"STDOUT:\n{result.stdout}")
            
            if result.stderr:
                output_parts.append(f"STDERR:\n{result.stderr}")
            
            # Store execution in memory
            await self.memory.store_text(
                text=f"Executed {script_type} script:\n{script_content}\nResult: {result.stdout}",
                metadata={
                    "type": "script_execution",
                    "agent": self.name,
                    "script_type": script_type,
                    "exit_code": result.exit_code
                }
            )
            
            return "\n".join(output_parts)
            
        except Exception as e:
            error_msg = f"Failed to execute {script_type} script: {str(e)}"
            
            # Store error in memory
            await self.memory.store_text(
                text=f"Script execution error: {script_type}\nError: {error_msg}",
                metadata={
                    "type": "script_error",
                    "agent": self.name,
                    "script_type": script_type
                }
            )
            
            return error_msg
    
    async def _execute_command(
        self,
        command: str,
        working_directory: str = None,
        timeout: int = 30,
        capture_output: bool = True
    ) -> str:
        """Function to execute command."""
        return await self._run_command(command, working_directory, timeout)
    
    async def _execute_script(
        self,
        script_content: str,
        script_type: str,
        timeout: int = 60
    ) -> str:
        """Function to execute script."""
        return await self._run_script(script_content, script_type)
    
    async def get_running_processes(self) -> str:
        """Get information about running processes."""
        
        processes = self.terminal_runner.get_running_processes()
        
        if not processes:
            return "No processes currently running"
        
        output = ["Currently running processes:"]
        for proc in processes:
            status = "Running" if proc["running"] else "Completed"
            output.append(f"  PID {proc['pid']}: {status}")
        
        return "\n".join(output)
    
    async def kill_all_processes(self) -> str:
        """Kill all running processes."""
        
        killed_count = await self.terminal_runner.kill_all_processes()
        return f"Killed {killed_count} processes"