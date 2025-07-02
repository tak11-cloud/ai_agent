"""
Security manager for command execution and system access.
"""

import re
import os
from typing import List, Set, Dict, Any
from dataclasses import dataclass


@dataclass
class SecurityPolicy:
    """Security policy configuration."""
    allowed_commands: Set[str]
    blocked_commands: Set[str]
    allowed_paths: List[str]
    blocked_paths: List[str]
    max_file_size: int
    max_execution_time: int
    allow_network: bool
    allow_system_modification: bool


class SecurityManager:
    """Manages security policies and command validation."""
    
    def __init__(self, policy: SecurityPolicy = None):
        self.policy = policy or self._get_default_policy()
        
        # Dangerous command patterns
        self.dangerous_patterns = [
            r'\brm\s+-rf\s+/',  # rm -rf /
            r'\bdd\s+if=',      # dd commands
            r'\bmkfs\.',        # filesystem creation
            r'\bfdisk\b',       # disk partitioning
            r'\bformat\b',      # format commands
            r'>\s*/dev/',       # writing to device files
            r'\bsudo\s+',       # sudo commands
            r'\bsu\s+',         # su commands
            r'\bchmod\s+777',   # dangerous permissions
            r'\bchown\s+root',  # ownership changes
            r'\bcurl.*\|\s*sh', # pipe to shell
            r'\bwget.*\|\s*sh', # pipe to shell
            r'\beval\s*\(',     # eval commands
            r'\bexec\s*\(',     # exec commands
            r';\s*rm\s+',       # chained rm commands
            r'&&\s*rm\s+',      # chained rm commands
            r'\|\s*rm\s+',      # piped rm commands
        ]
        
        # Network-related commands
        self.network_commands = {
            'curl', 'wget', 'nc', 'netcat', 'telnet', 'ssh', 'scp', 'rsync',
            'ftp', 'sftp', 'ping', 'nmap', 'dig', 'nslookup'
        }
        
        # System modification commands
        self.system_modification_commands = {
            'mount', 'umount', 'fdisk', 'parted', 'mkfs', 'fsck',
            'systemctl', 'service', 'chkconfig', 'update-rc.d',
            'iptables', 'ufw', 'firewall-cmd', 'setenforce'
        }
    
    def _get_default_policy(self) -> SecurityPolicy:
        """Get default security policy."""
        
        # Safe commands for development
        allowed_commands = {
            # File operations
            'ls', 'cat', 'head', 'tail', 'grep', 'find', 'locate',
            'file', 'stat', 'du', 'df', 'wc', 'sort', 'uniq',
            
            # Text processing
            'sed', 'awk', 'cut', 'tr', 'paste', 'join', 'diff',
            'patch', 'tee', 'less', 'more',
            
            # Development tools
            'git', 'python', 'python3', 'pip', 'pip3', 'node', 'npm',
            'yarn', 'make', 'cmake', 'gcc', 'g++', 'javac', 'java',
            'rustc', 'cargo', 'go', 'dotnet',
            
            # Archive operations
            'tar', 'gzip', 'gunzip', 'zip', 'unzip',
            
            # Process management (limited)
            'ps', 'top', 'htop', 'jobs', 'kill', 'killall',
            
            # System info
            'uname', 'whoami', 'id', 'groups', 'env', 'printenv',
            'date', 'uptime', 'free', 'lscpu', 'lsblk',
            
            # Network (limited)
            'ping', 'curl', 'wget',
            
            # Text editors
            'nano', 'vim', 'emacs',
            
            # Utilities
            'echo', 'printf', 'test', 'true', 'false', 'sleep',
            'timeout', 'which', 'type', 'command'
        }
        
        # Dangerous commands to block
        blocked_commands = {
            'rm', 'rmdir', 'dd', 'mkfs', 'fdisk', 'parted',
            'sudo', 'su', 'passwd', 'chpasswd', 'usermod',
            'mount', 'umount', 'systemctl', 'service',
            'iptables', 'ufw', 'firewall-cmd', 'setenforce',
            'reboot', 'shutdown', 'halt', 'poweroff',
            'crontab', 'at', 'batch'
        }
        
        return SecurityPolicy(
            allowed_commands=allowed_commands,
            blocked_commands=blocked_commands,
            allowed_paths=[
                '/tmp/agent_workspace',
                '/home/agent',
                '/workspace',
                '/app'
            ],
            blocked_paths=[
                '/etc',
                '/boot',
                '/sys',
                '/proc',
                '/dev',
                '/root',
                '/var/log'
            ],
            max_file_size=100 * 1024 * 1024,  # 100MB
            max_execution_time=300,  # 5 minutes
            allow_network=True,
            allow_system_modification=False
        )
    
    def is_command_safe(self, command: str) -> bool:
        """Check if a command is safe to execute."""
        
        # Check for dangerous patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return False
        
        # Parse command to get the base command
        base_command = self._extract_base_command(command)
        
        # Check if command is explicitly blocked
        if base_command in self.policy.blocked_commands:
            return False
        
        # Check if command is in allowed list
        if self.policy.allowed_commands and base_command not in self.policy.allowed_commands:
            return False
        
        # Check network restrictions
        if not self.policy.allow_network and base_command in self.network_commands:
            return False
        
        # Check system modification restrictions
        if not self.policy.allow_system_modification and base_command in self.system_modification_commands:
            return False
        
        # Check for path restrictions
        if not self._check_path_restrictions(command):
            return False
        
        return True
    
    def _extract_base_command(self, command: str) -> str:
        """Extract the base command from a command string."""
        
        # Remove leading/trailing whitespace
        command = command.strip()
        
        # Handle command substitution and pipes
        command = re.split(r'[|;&]', command)[0].strip()
        
        # Extract first word (the command)
        parts = command.split()
        if not parts:
            return ""
        
        base_cmd = parts[0]
        
        # Remove path if present
        if '/' in base_cmd:
            base_cmd = os.path.basename(base_cmd)
        
        return base_cmd
    
    def _check_path_restrictions(self, command: str) -> bool:
        """Check if command accesses restricted paths."""
        
        # Extract potential file paths from command
        path_patterns = [
            r'(/[^\s]*)',  # Absolute paths
            r'(\.\./[^\s]*)',  # Relative paths with ../
        ]
        
        paths = []
        for pattern in path_patterns:
            matches = re.findall(pattern, command)
            paths.extend(matches)
        
        # Check each path against restrictions
        for path in paths:
            # Resolve relative paths
            if not os.path.isabs(path):
                continue
            
            # Check if path is in blocked list
            for blocked_path in self.policy.blocked_paths:
                if path.startswith(blocked_path):
                    return False
            
            # If allowed paths are specified, check if path is allowed
            if self.policy.allowed_paths:
                allowed = False
                for allowed_path in self.policy.allowed_paths:
                    if path.startswith(allowed_path):
                        allowed = True
                        break
                if not allowed:
                    return False
        
        return True
    
    def sanitize_command(self, command: str) -> str:
        """Sanitize a command by removing dangerous elements."""
        
        # Remove dangerous patterns
        sanitized = command
        
        # Remove sudo/su prefixes
        sanitized = re.sub(r'^\s*(sudo|su)\s+', '', sanitized)
        
        # Remove pipe to shell patterns
        sanitized = re.sub(r'\|\s*(sh|bash|zsh|fish)\s*$', '', sanitized)
        
        # Remove command chaining with dangerous commands
        sanitized = re.sub(r'[;&|]+\s*(rm|dd|mkfs)\s+.*$', '', sanitized)
        
        return sanitized.strip()
    
    def validate_file_access(self, file_path: str, operation: str = "read") -> bool:
        """Validate file access permissions."""
        
        # Resolve absolute path
        abs_path = os.path.abspath(file_path)
        
        # Check blocked paths
        for blocked_path in self.policy.blocked_paths:
            if abs_path.startswith(blocked_path):
                return False
        
        # Check allowed paths
        if self.policy.allowed_paths:
            allowed = False
            for allowed_path in self.policy.allowed_paths:
                if abs_path.startswith(allowed_path):
                    allowed = True
                    break
            if not allowed:
                return False
        
        # Check file size for write operations
        if operation in ["write", "append"] and os.path.exists(abs_path):
            try:
                file_size = os.path.getsize(abs_path)
                if file_size > self.policy.max_file_size:
                    return False
            except OSError:
                pass
        
        return True
    
    def get_safe_environment(self) -> Dict[str, str]:
        """Get a safe environment for command execution."""
        
        safe_env = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": "/tmp/agent_workspace",
            "USER": "agent",
            "SHELL": "/bin/bash",
            "TERM": "xterm-256color",
            "LANG": "en_US.UTF-8",
            "LC_ALL": "en_US.UTF-8"
        }
        
        # Remove potentially dangerous environment variables
        dangerous_vars = {
            "LD_PRELOAD", "LD_LIBRARY_PATH", "PYTHONPATH",
            "PERL5LIB", "RUBYLIB", "NODE_PATH"
        }
        
        return safe_env
    
    def log_security_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Log security events for monitoring."""
        
        # In a full implementation, this would log to a security monitoring system
        print(f"SECURITY EVENT: {event_type} - {details}")
    
    def update_policy(self, policy_updates: Dict[str, Any]) -> None:
        """Update security policy."""
        
        for key, value in policy_updates.items():
            if hasattr(self.policy, key):
                setattr(self.policy, key, value)