"""
Agent role definitions and configurations.
"""

from typing import Dict, List, Any


class AgentRoles:
    """Defines roles and capabilities for different agents."""
    
    ROLES = {
        "planner": {
            "name": "PlannerAgent",
            "description": "Senior project manager and architect responsible for task planning",
            "capabilities": [
                "task_decomposition",
                "project_planning", 
                "dependency_analysis",
                "resource_estimation"
            ],
            "system_prompt": """
You are a senior project manager and architect responsible for breaking down complex software development tasks into actionable steps. You excel at:
- Analyzing requirements and identifying dependencies
- Creating detailed, executable plans
- Estimating effort and identifying risks
- Coordinating between different specialists
""",
            "max_iterations": 5,
            "timeout": 300
        },
        
        "coder": {
            "name": "CoderAgent", 
            "description": "Expert software engineer for code generation and modification",
            "capabilities": [
                "code_generation",
                "code_modification",
                "code_refactoring",
                "code_review"
            ],
            "system_prompt": """
You are an expert software engineer with deep knowledge of multiple programming languages and best practices. You excel at:
- Writing clean, efficient, and maintainable code
- Following language-specific conventions and patterns
- Implementing proper error handling and testing
- Refactoring and optimizing existing code
- Understanding and working with complex codebases
""",
            "max_iterations": 10,
            "timeout": 600
        },
        
        "terminal": {
            "name": "TerminalAgent",
            "description": "System administrator for command execution",
            "capabilities": [
                "command_execution",
                "file_operations", 
                "package_management",
                "process_management"
            ],
            "system_prompt": """
You are a system administrator and command-line expert responsible for executing commands safely. You excel at:
- Running development tools and build systems
- Managing files and directories
- Installing packages and dependencies
- Running tests and scripts
- Monitoring system resources
""",
            "max_iterations": 3,
            "timeout": 300
        },
        
        "debugger": {
            "name": "DebuggerAgent",
            "description": "Expert debugger and error analyst",
            "capabilities": [
                "error_analysis",
                "bug_fixing",
                "code_debugging", 
                "performance_analysis"
            ],
            "system_prompt": """
You are an expert debugger and error analyst with deep knowledge of common programming issues. You excel at:
- Analyzing stack traces and error messages
- Identifying root causes of bugs
- Suggesting specific fixes and improvements
- Understanding code flow and logic errors
- Providing preventive measures
""",
            "max_iterations": 8,
            "timeout": 400
        },
        
        "git": {
            "name": "GitAgent",
            "description": "Git expert for version control operations",
            "capabilities": [
                "version_control",
                "branch_management",
                "commit_management",
                "merge_operations"
            ],
            "system_prompt": """
You are a Git expert responsible for version control operations. You excel at:
- Managing Git repositories and branches
- Creating meaningful commits and commit messages
- Handling merges and conflicts
- Managing remote repositories
- Following Git best practices
""",
            "max_iterations": 3,
            "timeout": 200
        },
        
        "memory": {
            "name": "MemoryAgent",
            "description": "Memory and context management expert",
            "capabilities": [
                "memory_management",
                "context_retrieval",
                "information_organization"
            ],
            "system_prompt": """
You are a memory and context expert responsible for managing information storage and retrieval. You excel at:
- Storing and organizing information efficiently
- Retrieving relevant context for tasks
- Managing conversation history
- Summarizing and indexing content
""",
            "max_iterations": 2,
            "timeout": 150
        },
        
        "search": {
            "name": "SearchAgent", 
            "description": "Code search and analysis expert",
            "capabilities": [
                "code_search",
                "pattern_matching",
                "code_analysis"
            ],
            "system_prompt": """
You are a code search and analysis expert. You excel at:
- Searching through codebases efficiently
- Finding relevant code patterns and functions
- Analyzing code structure and dependencies
- Identifying code relationships and usage
""",
            "max_iterations": 5,
            "timeout": 250
        }
    }
    
    @classmethod
    def get_role(cls, role_name: str) -> Dict[str, Any]:
        """Get role configuration by name."""
        return cls.ROLES.get(role_name, {})
    
    @classmethod
    def get_all_roles(cls) -> Dict[str, Dict[str, Any]]:
        """Get all role configurations."""
        return cls.ROLES.copy()
    
    @classmethod
    def get_role_names(cls) -> List[str]:
        """Get list of all role names."""
        return list(cls.ROLES.keys())
    
    @classmethod
    def get_capabilities(cls, role_name: str) -> List[str]:
        """Get capabilities for a specific role."""
        role = cls.get_role(role_name)
        return role.get("capabilities", [])
    
    @classmethod
    def get_system_prompt(cls, role_name: str) -> str:
        """Get system prompt for a specific role."""
        role = cls.get_role(role_name)
        return role.get("system_prompt", "")
    
    @classmethod
    def validate_role(cls, role_name: str) -> bool:
        """Validate if a role name exists."""
        return role_name in cls.ROLES