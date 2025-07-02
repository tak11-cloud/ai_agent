"""
Coder Agent - Generates, modifies, and refactors code.
"""

import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent, AgentThought
from llm_engine import FunctionSchema
from tools.code_parser import CodeParser
from tools.file_manager import FileManager


@dataclass
class CodeChange:
    """Represents a code change."""
    file_path: str
    change_type: str  # create, modify, delete
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    description: str = ""


class CoderAgent(BaseAgent):
    """Agent responsible for code generation and modification."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role_description = """
You are an expert software engineer with deep knowledge of multiple programming languages and best practices. You excel at:
- Writing clean, efficient, and maintainable code
- Following language-specific conventions and patterns
- Implementing proper error handling and testing
- Refactoring and optimizing existing code
- Understanding and working with complex codebases
"""
        self.add_capability("code_generation")
        self.add_capability("code_modification")
        self.add_capability("code_refactoring")
        self.add_capability("code_review")
        
        # Initialize tools
        self.code_parser = CodeParser()
        self.file_manager = FileManager()
    
    def _setup_functions(self) -> None:
        """Setup coder-specific functions."""
        
        # Generate code function
        generate_code_schema = FunctionSchema(
            name="generate_code",
            description="Generate new code based on requirements",
            parameters={
                "language": {
                    "type": "string",
                    "description": "Programming language (python, javascript, etc.)"
                },
                "requirements": {
                    "type": "string",
                    "description": "Detailed requirements for the code"
                },
                "file_path": {
                    "type": "string",
                    "description": "Path where the code should be saved"
                },
                "context": {
                    "type": "string",
                    "description": "Additional context about the codebase"
                }
            },
            required=["language", "requirements", "file_path"]
        )
        
        self.function_caller.register_function(
            self._generate_code,
            generate_code_schema
        )
        
        # Modify code function
        modify_code_schema = FunctionSchema(
            name="modify_code",
            description="Modify existing code",
            parameters={
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to modify"
                },
                "changes": {
                    "type": "string",
                    "description": "Description of changes to make"
                },
                "target_function": {
                    "type": "string",
                    "description": "Specific function or class to modify (optional)"
                }
            },
            required=["file_path", "changes"]
        )
        
        self.function_caller.register_function(
            self._modify_code,
            modify_code_schema
        )
        
        # Refactor code function
        refactor_code_schema = FunctionSchema(
            name="refactor_code",
            description="Refactor code for better structure and maintainability",
            parameters={
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to refactor"
                },
                "refactor_type": {
                    "type": "string",
                    "description": "Type of refactoring (extract_method, rename, etc.)"
                },
                "target": {
                    "type": "string",
                    "description": "Specific code element to refactor"
                }
            },
            required=["file_path", "refactor_type"]
        )
        
        self.function_caller.register_function(
            self._refactor_code,
            refactor_code_schema
        )
    
    async def _think(self, observation: str) -> AgentThought:
        """Generate coding thoughts."""
        
        # Get relevant context from memory
        context = await self.get_relevant_context(observation)
        context_str = "\n".join(context) if context else "No relevant context found."
        
        # Analyze the observation to determine the type of coding task
        task_type = self._analyze_task_type(observation)
        
        # Build appropriate prompt based on task type
        if task_type == "generation":
            prompt = self.prompt_builder.build_prompt(
                "code_generation",
                requirements=observation,
                context=context_str,
                language="python"  # Default, should be detected
            )
        elif task_type == "modification":
            prompt = self.prompt_builder.build_prompt(
                "code_modification",
                requirements=observation,
                context=context_str
            )
        else:
            # General coding prompt
            prompt = f"""
You are an expert software engineer. Analyze this coding task:

TASK: {observation}

CONTEXT: {context_str}

Determine what needs to be done and plan your approach. Consider:
1. What type of code changes are needed?
2. Which files need to be modified or created?
3. What are the technical requirements?
4. Are there any dependencies or constraints?

Provide your analysis and planned action.
"""
        
        # Get LLM response
        response = await self.llm.generate(prompt)
        
        # Parse response for action
        action = self._extract_action_from_response(response.content)
        action_input = self._extract_action_input(response.content, observation)
        
        return AgentThought(
            observation=observation,
            thought=response.content,
            action=action,
            action_input=action_input
        )
    
    async def _act(self, thought: AgentThought) -> str:
        """Execute coding action."""
        
        if thought.action == "generate_code":
            return await self._handle_code_generation(thought)
        elif thought.action == "modify_code":
            return await self._handle_code_modification(thought)
        elif thought.action == "refactor_code":
            return await self._handle_code_refactoring(thought)
        else:
            # Use function calling
            function_calls = self.function_caller.parse_function_calls(thought.thought)
            if function_calls:
                results = await self.function_caller.execute_function_calls(function_calls)
                return self.function_caller.format_function_results(results)
            else:
                return f"Analyzed coding requirements: {thought.thought}"
    
    def _analyze_task_type(self, observation: str) -> str:
        """Analyze what type of coding task this is."""
        
        observation_lower = observation.lower()
        
        if any(word in observation_lower for word in ["create", "generate", "write", "implement", "add new"]):
            return "generation"
        elif any(word in observation_lower for word in ["modify", "change", "update", "fix", "edit"]):
            return "modification"
        elif any(word in observation_lower for word in ["refactor", "restructure", "optimize", "improve"]):
            return "refactoring"
        else:
            return "analysis"
    
    def _extract_action_from_response(self, response: str) -> str:
        """Extract the intended action from LLM response."""
        
        response_lower = response.lower()
        
        if "generate" in response_lower or "create" in response_lower:
            return "generate_code"
        elif "modify" in response_lower or "change" in response_lower:
            return "modify_code"
        elif "refactor" in response_lower:
            return "refactor_code"
        else:
            return "analyze_code"
    
    def _extract_action_input(self, response: str, observation: str) -> Dict[str, Any]:
        """Extract action input parameters from response."""
        
        # Try to extract file paths
        file_pattern = r'(?:file|path):\s*([^\s\n]+)'
        file_matches = re.findall(file_pattern, response, re.IGNORECASE)
        
        # Try to extract language
        lang_pattern = r'(?:language|lang):\s*(\w+)'
        lang_matches = re.findall(lang_pattern, response, re.IGNORECASE)
        
        return {
            "file_path": file_matches[0] if file_matches else "",
            "language": lang_matches[0] if lang_matches else "python",
            "requirements": observation,
            "context": response
        }
    
    async def _handle_code_generation(self, thought: AgentThought) -> str:
        """Handle code generation task."""
        
        file_path = thought.action_input.get("file_path", "")
        language = thought.action_input.get("language", "python")
        requirements = thought.action_input.get("requirements", "")
        
        if not file_path:
            # Try to infer file path from requirements
            file_path = self._infer_file_path(requirements, language)
        
        # Generate code using LLM
        code_prompt = f"""
Generate high-quality {language} code for the following requirements:

REQUIREMENTS:
{requirements}

GUIDELINES:
- Follow {language} best practices and conventions
- Include proper error handling
- Add clear but minimal comments
- Ensure code is production-ready
- Include type hints if applicable

Generate only the code, no explanations:
"""
        
        response = await self.llm.generate(code_prompt)
        generated_code = self._extract_code_from_response(response.content)
        
        # Save the code if file path is provided
        if file_path:
            try:
                await self.file_manager.write_file(file_path, generated_code)
                result = f"Generated code saved to {file_path}\n\nCode:\n{generated_code}"
            except Exception as e:
                result = f"Generated code (failed to save to {file_path}: {e}):\n{generated_code}"
        else:
            result = f"Generated code:\n{generated_code}"
        
        # Store in memory
        await self.memory.store_text(
            text=f"Generated code for: {requirements}\n\n{generated_code}",
            metadata={
                "type": "code_generation",
                "agent": self.name,
                "file_path": file_path,
                "language": language
            }
        )
        
        return result
    
    async def _handle_code_modification(self, thought: AgentThought) -> str:
        """Handle code modification task."""
        
        file_path = thought.action_input.get("file_path", "")
        changes = thought.action_input.get("requirements", "")
        
        if not file_path:
            return "Error: No file path specified for modification"
        
        try:
            # Read existing code
            existing_code = await self.file_manager.read_file(file_path)
            
            # Generate modification prompt
            modify_prompt = f"""
Modify the following code according to the requirements:

EXISTING CODE:
```
{existing_code}
```

MODIFICATION REQUIREMENTS:
{changes}

GUIDELINES:
- Preserve existing functionality unless explicitly changing it
- Maintain code style and conventions
- Add proper error handling for new code
- Ensure all changes are backward compatible where possible

Provide the complete modified code:
"""
            
            response = await self.llm.generate(modify_prompt)
            modified_code = self._extract_code_from_response(response.content)
            
            # Save modified code
            await self.file_manager.write_file(file_path, modified_code)
            
            # Store change in memory
            await self.memory.store_text(
                text=f"Modified {file_path}: {changes}\n\nNew code:\n{modified_code}",
                metadata={
                    "type": "code_modification",
                    "agent": self.name,
                    "file_path": file_path
                }
            )
            
            return f"Successfully modified {file_path}\n\nChanges: {changes}"
            
        except Exception as e:
            return f"Error modifying code: {str(e)}"
    
    async def _handle_code_refactoring(self, thought: AgentThought) -> str:
        """Handle code refactoring task."""
        
        file_path = thought.action_input.get("file_path", "")
        refactor_type = thought.action_input.get("refactor_type", "general")
        
        if not file_path:
            return "Error: No file path specified for refactoring"
        
        try:
            # Read existing code
            existing_code = await self.file_manager.read_file(file_path)
            
            # Generate refactoring prompt
            refactor_prompt = f"""
Refactor the following code to improve its structure and maintainability:

EXISTING CODE:
```
{existing_code}
```

REFACTORING TYPE: {refactor_type}

GUIDELINES:
- Improve code readability and maintainability
- Extract reusable functions/methods where appropriate
- Reduce code duplication
- Improve naming conventions
- Maintain all existing functionality
- Add type hints and documentation where beneficial

Provide the refactored code:
"""
            
            response = await self.llm.generate(refactor_prompt)
            refactored_code = self._extract_code_from_response(response.content)
            
            # Save refactored code
            await self.file_manager.write_file(file_path, refactored_code)
            
            # Store refactoring in memory
            await self.memory.store_text(
                text=f"Refactored {file_path} ({refactor_type}):\n\n{refactored_code}",
                metadata={
                    "type": "code_refactoring",
                    "agent": self.name,
                    "file_path": file_path,
                    "refactor_type": refactor_type
                }
            )
            
            return f"Successfully refactored {file_path} ({refactor_type})"
            
        except Exception as e:
            return f"Error refactoring code: {str(e)}"
    
    def _extract_code_from_response(self, response: str) -> str:
        """Extract code from LLM response."""
        
        # Look for code blocks
        code_pattern = r'```(?:\w+)?\n(.*?)\n```'
        matches = re.findall(code_pattern, response, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        # If no code blocks found, try to extract code-like content
        lines = response.split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            # Skip explanatory text
            if any(word in line.lower() for word in ['here', 'this', 'the code', 'explanation']):
                continue
            
            # Look for code patterns
            if (line.strip().startswith(('def ', 'class ', 'import ', 'from ')) or
                '=' in line or '(' in line or '{' in line):
                in_code = True
            
            if in_code:
                code_lines.append(line)
        
        return '\n'.join(code_lines).strip() if code_lines else response.strip()
    
    def _infer_file_path(self, requirements: str, language: str) -> str:
        """Infer file path from requirements."""
        
        # Extract potential file names from requirements
        file_pattern = r'(\w+\.(?:py|js|ts|java|cpp|c|h|go|rs|rb))'
        matches = re.findall(file_pattern, requirements)
        
        if matches:
            return matches[0]
        
        # Generate file name based on requirements
        words = re.findall(r'\w+', requirements.lower())
        if words:
            name = '_'.join(words[:3])  # Use first 3 words
            extensions = {
                'python': '.py',
                'javascript': '.js',
                'typescript': '.ts',
                'java': '.java',
                'cpp': '.cpp',
                'c': '.c',
                'go': '.go',
                'rust': '.rs',
                'ruby': '.rb'
            }
            ext = extensions.get(language, '.py')
            return f"{name}{ext}"
        
        return f"generated_code.{language}"
    
    async def _generate_code(self, language: str, requirements: str, file_path: str, context: str = "") -> str:
        """Function to generate code."""
        return await self._handle_code_generation(AgentThought(
            observation=requirements,
            thought=f"Generate {language} code",
            action="generate_code",
            action_input={
                "language": language,
                "requirements": requirements,
                "file_path": file_path,
                "context": context
            }
        ))
    
    async def _modify_code(self, file_path: str, changes: str, target_function: str = "") -> str:
        """Function to modify code."""
        return await self._handle_code_modification(AgentThought(
            observation=changes,
            thought=f"Modify code in {file_path}",
            action="modify_code",
            action_input={
                "file_path": file_path,
                "requirements": changes,
                "target_function": target_function
            }
        ))
    
    async def _refactor_code(self, file_path: str, refactor_type: str, target: str = "") -> str:
        """Function to refactor code."""
        return await self._handle_code_refactoring(AgentThought(
            observation=f"Refactor {file_path}",
            thought=f"Refactor code using {refactor_type}",
            action="refactor_code",
            action_input={
                "file_path": file_path,
                "refactor_type": refactor_type,
                "target": target
            }
        ))