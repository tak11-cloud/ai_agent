"""
Function calling system with JSON schema validation.
"""

import json
import re
from typing import Dict, List, Any, Optional, Callable
from pydantic import BaseModel, ValidationError
from dataclasses import dataclass


@dataclass
class FunctionSchema:
    """Schema for a callable function."""
    name: str
    description: str
    parameters: Dict[str, Any]
    required: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": self.parameters,
                "required": self.required or []
            }
        }


class FunctionCall(BaseModel):
    """Represents a function call."""
    function: str
    parameters: Dict[str, Any]
    call_id: Optional[str] = None


class FunctionResult(BaseModel):
    """Result of a function call."""
    call_id: Optional[str] = None
    function: str
    result: Any
    success: bool
    error: Optional[str] = None


class FunctionCaller:
    """Manages function calling with LLMs."""
    
    def __init__(self):
        self.functions: Dict[str, Callable] = {}
        self.schemas: Dict[str, FunctionSchema] = {}
    
    def register_function(
        self,
        func: Callable,
        schema: FunctionSchema
    ) -> None:
        """Register a function with its schema."""
        self.functions[schema.name] = func
        self.schemas[schema.name] = schema
    
    def get_function_schemas(self) -> List[Dict[str, Any]]:
        """Get all function schemas for LLM."""
        return [schema.to_dict() for schema in self.schemas.values()]
    
    def parse_function_calls(self, text: str) -> List[FunctionCall]:
        """Parse function calls from LLM response."""
        function_calls = []
        
        # Look for JSON blocks in the text
        json_pattern = r'```json\s*(\{.*?\})\s*```'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                data = json.loads(match)
                if "function" in data and "parameters" in data:
                    function_calls.append(FunctionCall(
                        function=data["function"],
                        parameters=data["parameters"],
                        call_id=data.get("call_id")
                    ))
            except json.JSONDecodeError:
                continue
        
        # Also look for direct JSON objects
        if not function_calls:
            try:
                # Try to parse the entire text as JSON
                data = json.loads(text.strip())
                if isinstance(data, dict) and "function" in data:
                    function_calls.append(FunctionCall(
                        function=data["function"],
                        parameters=data["parameters"],
                        call_id=data.get("call_id")
                    ))
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "function" in item:
                            function_calls.append(FunctionCall(
                                function=item["function"],
                                parameters=item["parameters"],
                                call_id=item.get("call_id")
                            ))
            except json.JSONDecodeError:
                pass
        
        return function_calls
    
    async def execute_function_call(self, call: FunctionCall) -> FunctionResult:
        """Execute a function call."""
        if call.function not in self.functions:
            return FunctionResult(
                call_id=call.call_id,
                function=call.function,
                result=None,
                success=False,
                error=f"Function '{call.function}' not found"
            )
        
        try:
            func = self.functions[call.function]
            
            # Execute function (handle both sync and async)
            if hasattr(func, '__call__'):
                if hasattr(func, '__await__'):
                    result = await func(**call.parameters)
                else:
                    result = func(**call.parameters)
            else:
                result = func(**call.parameters)
            
            return FunctionResult(
                call_id=call.call_id,
                function=call.function,
                result=result,
                success=True
            )
        
        except Exception as e:
            return FunctionResult(
                call_id=call.call_id,
                function=call.function,
                result=None,
                success=False,
                error=str(e)
            )
    
    async def execute_function_calls(self, calls: List[FunctionCall]) -> List[FunctionResult]:
        """Execute multiple function calls."""
        results = []
        for call in calls:
            result = await self.execute_function_call(call)
            results.append(result)
        return results
    
    def format_function_results(self, results: List[FunctionResult]) -> str:
        """Format function results for LLM."""
        formatted_results = []
        
        for result in results:
            if result.success:
                formatted_results.append(
                    f"Function '{result.function}' executed successfully:\n"
                    f"Result: {json.dumps(result.result, indent=2)}"
                )
            else:
                formatted_results.append(
                    f"Function '{result.function}' failed:\n"
                    f"Error: {result.error}"
                )
        
        return "\n\n".join(formatted_results)


# Common function schemas
COMMON_SCHEMAS = {
    "execute_command": FunctionSchema(
        name="execute_command",
        description="Execute a shell command in the terminal",
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
            }
        },
        required=["command"]
    ),
    
    "read_file": FunctionSchema(
        name="read_file",
        description="Read the contents of a file",
        parameters={
            "file_path": {
                "type": "string",
                "description": "Path to the file to read"
            }
        },
        required=["file_path"]
    ),
    
    "write_file": FunctionSchema(
        name="write_file", 
        description="Write content to a file",
        parameters={
            "file_path": {
                "type": "string",
                "description": "Path to the file to write"
            },
            "content": {
                "type": "string",
                "description": "Content to write to the file"
            },
            "mode": {
                "type": "string",
                "description": "Write mode: 'w' for overwrite, 'a' for append",
                "enum": ["w", "a"]
            }
        },
        required=["file_path", "content"]
    ),
    
    "search_code": FunctionSchema(
        name="search_code",
        description="Search for code patterns in the codebase",
        parameters={
            "query": {
                "type": "string",
                "description": "Search query or pattern"
            },
            "file_pattern": {
                "type": "string", 
                "description": "File pattern to search in (e.g., '*.py')"
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Whether search should be case sensitive"
            }
        },
        required=["query"]
    ),
    
    "git_commit": FunctionSchema(
        name="git_commit",
        description="Commit changes to git repository",
        parameters={
            "message": {
                "type": "string",
                "description": "Commit message"
            },
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of files to commit (empty for all)"
            }
        },
        required=["message"]
    )
}