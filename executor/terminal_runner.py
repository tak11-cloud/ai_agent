"""
Terminal command execution with sandboxing and security controls.
"""

import asyncio
import subprocess
import shlex
import os
import signal
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

from .security_manager import SecurityManager


@dataclass
class CommandResult:
    """Result of command execution."""
    command: str
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    working_directory: str
    environment: Dict[str, str]
    timestamp: datetime
    timeout: bool = False
    killed: bool = False


class TerminalRunner:
    """Secure terminal command execution."""
    
    def __init__(
        self,
        working_directory: str = "/tmp/agent_workspace",
        default_timeout: int = 30,
        max_output_size: int = 1024 * 1024,  # 1MB
        use_sandbox: bool = True
    ):
        self.working_directory = working_directory
        self.default_timeout = default_timeout
        self.max_output_size = max_output_size
        self.use_sandbox = use_sandbox
        
        self.security_manager = SecurityManager()
        self.running_processes: Dict[str, subprocess.Popen] = {}
        
        # Create working directory
        os.makedirs(working_directory, exist_ok=True)
        
        # Environment variables
        self.base_environment = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": working_directory,
            "USER": "agent",
            "SHELL": "/bin/bash",
            "TERM": "xterm-256color",
            "LANG": "en_US.UTF-8"
        }
    
    async def execute_command(
        self,
        command: str,
        working_directory: Optional[str] = None,
        timeout: Optional[int] = None,
        environment: Optional[Dict[str, str]] = None,
        capture_output: bool = True,
        shell: bool = False
    ) -> CommandResult:
        """Execute a command with security checks."""
        
        start_time = datetime.now()
        working_dir = working_directory or self.working_directory
        timeout_seconds = timeout or self.default_timeout
        
        # Security check
        if not self.security_manager.is_command_safe(command):
            return CommandResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Command blocked by security policy: {command}",
                execution_time=0.0,
                working_directory=working_dir,
                environment=environment or {},
                timestamp=start_time
            )
        
        # Prepare environment
        env = self.base_environment.copy()
        if environment:
            env.update(environment)
        
        # Prepare command
        if not shell:
            try:
                cmd_args = shlex.split(command)
            except ValueError as e:
                return CommandResult(
                    command=command,
                    exit_code=-1,
                    stdout="",
                    stderr=f"Invalid command syntax: {e}",
                    execution_time=0.0,
                    working_directory=working_dir,
                    environment=env,
                    timestamp=start_time
                )
        else:
            cmd_args = command
        
        try:
            # Execute command
            if self.use_sandbox:
                result = await self._execute_in_sandbox(
                    cmd_args, working_dir, env, timeout_seconds, capture_output, shell
                )
            else:
                result = await self._execute_direct(
                    cmd_args, working_dir, env, timeout_seconds, capture_output, shell
                )
            
            # Calculate execution time
            end_time = datetime.now()
            result.execution_time = (end_time - start_time).total_seconds()
            result.timestamp = start_time
            
            return result
            
        except Exception as e:
            end_time = datetime.now()
            return CommandResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Execution error: {str(e)}",
                execution_time=(end_time - start_time).total_seconds(),
                working_directory=working_dir,
                environment=env,
                timestamp=start_time
            )
    
    async def _execute_direct(
        self,
        cmd_args,
        working_dir: str,
        env: Dict[str, str],
        timeout_seconds: int,
        capture_output: bool,
        shell: bool
    ) -> CommandResult:
        """Execute command directly on host system."""
        
        process = None
        stdout_data = ""
        stderr_data = ""
        timeout_occurred = False
        killed = False
        
        try:
            # Start process
            process = await asyncio.create_subprocess_exec(
                *cmd_args if not shell else ["/bin/bash", "-c", cmd_args],
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
                cwd=working_dir,
                env=env,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            
            # Store process for potential termination
            process_id = str(id(process))
            self.running_processes[process_id] = process
            
            try:
                # Wait for completion with timeout
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout_seconds
                )
                
                if capture_output:
                    stdout_data = stdout_bytes.decode('utf-8', errors='replace')
                    stderr_data = stderr_bytes.decode('utf-8', errors='replace')
                    
                    # Truncate output if too large
                    if len(stdout_data) > self.max_output_size:
                        stdout_data = stdout_data[:self.max_output_size] + "\n... (output truncated)"
                    if len(stderr_data) > self.max_output_size:
                        stderr_data = stderr_data[:self.max_output_size] + "\n... (output truncated)"
                
            except asyncio.TimeoutError:
                timeout_occurred = True
                # Kill process group
                try:
                    if os.name != 'nt':
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    else:
                        process.terminate()
                    
                    # Wait a bit for graceful termination
                    try:
                        await asyncio.wait_for(process.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        # Force kill
                        if os.name != 'nt':
                            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                        else:
                            process.kill()
                        killed = True
                        
                except (ProcessLookupError, PermissionError):
                    pass
                
                stderr_data = f"Command timed out after {timeout_seconds} seconds"
            
            finally:
                # Remove from running processes
                self.running_processes.pop(process_id, None)
            
            return CommandResult(
                command=" ".join(cmd_args) if isinstance(cmd_args, list) else cmd_args,
                exit_code=process.returncode or -1,
                stdout=stdout_data,
                stderr=stderr_data,
                execution_time=0.0,  # Will be set by caller
                working_directory=working_dir,
                environment=env,
                timestamp=datetime.now(),
                timeout=timeout_occurred,
                killed=killed
            )
            
        except Exception as e:
            return CommandResult(
                command=" ".join(cmd_args) if isinstance(cmd_args, list) else cmd_args,
                exit_code=-1,
                stdout="",
                stderr=f"Process execution error: {str(e)}",
                execution_time=0.0,
                working_directory=working_dir,
                environment=env,
                timestamp=datetime.now()
            )
    
    async def _execute_in_sandbox(
        self,
        cmd_args,
        working_dir: str,
        env: Dict[str, str],
        timeout_seconds: int,
        capture_output: bool,
        shell: bool
    ) -> CommandResult:
        """Execute command in Docker sandbox."""
        
        # For now, fall back to direct execution
        # In a full implementation, this would use DockerSandbox
        return await self._execute_direct(
            cmd_args, working_dir, env, timeout_seconds, capture_output, shell
        )
    
    async def execute_script(
        self,
        script_content: str,
        script_type: str = "bash",
        **kwargs
    ) -> CommandResult:
        """Execute a script."""
        
        # Write script to temporary file
        import tempfile
        
        script_extensions = {
            "bash": ".sh",
            "python": ".py",
            "javascript": ".js",
            "node": ".js"
        }
        
        ext = script_extensions.get(script_type, ".sh")
        
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=ext,
            dir=self.working_directory,
            delete=False
        ) as f:
            f.write(script_content)
            script_path = f.name
        
        try:
            # Make script executable
            os.chmod(script_path, 0o755)
            
            # Execute script
            if script_type == "python":
                command = f"python3 {script_path}"
            elif script_type in ["javascript", "node"]:
                command = f"node {script_path}"
            else:
                command = f"bash {script_path}"
            
            result = await self.execute_command(command, **kwargs)
            
            return result
            
        finally:
            # Clean up script file
            try:
                os.unlink(script_path)
            except OSError:
                pass
    
    async def kill_all_processes(self) -> int:
        """Kill all running processes."""
        
        killed_count = 0
        
        for process_id, process in list(self.running_processes.items()):
            try:
                if process.returncode is None:  # Still running
                    if os.name != 'nt':
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    else:
                        process.terminate()
                    killed_count += 1
            except (ProcessLookupError, PermissionError):
                pass
            
            self.running_processes.pop(process_id, None)
        
        return killed_count
    
    def get_running_processes(self) -> List[Dict[str, Any]]:
        """Get information about running processes."""
        
        processes = []
        
        for process_id, process in self.running_processes.items():
            processes.append({
                "id": process_id,
                "pid": process.pid,
                "returncode": process.returncode,
                "running": process.returncode is None
            })
        
        return processes
    
    async def test_command_execution(self) -> bool:
        """Test if command execution is working."""
        
        try:
            result = await self.execute_command("echo 'test'", timeout=5)
            return result.exit_code == 0 and "test" in result.stdout
        except Exception:
            return False
    
    def set_working_directory(self, directory: str) -> None:
        """Set the default working directory."""
        
        os.makedirs(directory, exist_ok=True)
        self.working_directory = directory
        self.base_environment["HOME"] = directory
    
    def add_environment_variable(self, key: str, value: str) -> None:
        """Add an environment variable."""
        
        self.base_environment[key] = value
    
    def get_environment(self) -> Dict[str, str]:
        """Get current environment variables."""
        
        return self.base_environment.copy()