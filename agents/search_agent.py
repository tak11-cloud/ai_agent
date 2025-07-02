"""
Search Agent - Searches and analyzes codebase.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from agents.base_agent import BaseAgent, AgentThought
from llm_engine import FunctionSchema
from tools.file_manager import FileManager
from tools.code_parser import CodeParser


@dataclass
class SearchResult:
    """Represents a search result."""
    file_path: str
    line_number: int
    content: str
    context: str
    match_type: str


class SearchAgent(BaseAgent):
    """Agent responsible for code search and analysis."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role_description = "Code search and analysis expert"
        self.add_capability("code_search")
        self.add_capability("pattern_matching")
        self.add_capability("code_analysis")
        
        # Initialize tools
        self.file_manager: Optional[FileManager] = None
        self.code_parser: Optional[CodeParser] = None
    
    def _setup_functions(self):
        """Setup search-specific functions."""
        
        self.add_function(FunctionSchema(
            name="search_code",
            description="Search for code patterns or text in files",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query or pattern"},
                    "file_pattern": {"type": "string", "description": "File pattern to search in"},
                    "search_type": {"type": "string", "enum": ["text", "regex", "function", "class"]}
                },
                "required": ["query"]
            }
        ))
        
        self.add_function(FunctionSchema(
            name="find_function",
            description="Find function definitions",
            parameters={
                "type": "object",
                "properties": {
                    "function_name": {"type": "string", "description": "Name of function to find"},
                    "language": {"type": "string", "description": "Programming language"}
                },
                "required": ["function_name"]
            }
        ))
        
        self.add_function(FunctionSchema(
            name="find_references",
            description="Find references to a symbol",
            parameters={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Symbol to find references for"},
                    "symbol_type": {"type": "string", "enum": ["function", "class", "variable"]}
                },
                "required": ["symbol"]
            }
        ))
        
        self.add_function(FunctionSchema(
            name="analyze_dependencies",
            description="Analyze code dependencies",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "File to analyze"},
                    "analysis_type": {"type": "string", "enum": ["imports", "calls", "inheritance"]}
                },
                "required": ["file_path"]
            }
        ))
    
    async def _think(self, observation: str) -> AgentThought:
        """Think about search operations."""
        
        # Analyze what search operations are needed
        if "find" in observation.lower() or "search" in observation.lower():
            if "function" in observation.lower():
                action_type = "find_function"
                reasoning = "Need to find function definitions"
            elif "class" in observation.lower():
                action_type = "find_class"
                reasoning = "Need to find class definitions"
            elif "reference" in observation.lower():
                action_type = "find_references"
                reasoning = "Need to find symbol references"
            else:
                action_type = "search_code"
                reasoning = "Need to search for code patterns"
        elif "analyze" in observation.lower() or "dependency" in observation.lower():
            action_type = "analyze_dependencies"
            reasoning = "Need to analyze code dependencies"
        else:
            action_type = "general_search"
            reasoning = "Analyzing search requirements"
        
        return AgentThought(
            observation=observation,
            reasoning=reasoning,
            action_type=action_type,
            confidence=0.8
        )
    
    async def _act(self, thought: AgentThought) -> str:
        """Execute search operations."""
        
        if thought.action_type == "search_code":
            return await self._search_code(thought.observation)
        elif thought.action_type == "find_function":
            return await self._find_function(thought.observation)
        elif thought.action_type == "find_references":
            return await self._find_references(thought.observation)
        elif thought.action_type == "analyze_dependencies":
            return await self._analyze_dependencies(thought.observation)
        else:
            return "Search agent ready to help with code search and analysis."
    
    async def _search_code(self, query: str) -> str:
        """Search for code patterns."""
        
        if not self.file_manager:
            return "File manager not available"
        
        try:
            # Get all files
            files = await self.file_manager.list_files()
            results = []
            
            # Search in each file
            for file_path in files:
                if file_path.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.c', '.h')):
                    try:
                        content = await self.file_manager.read_file(file_path)
                        lines = content.split('\n')
                        
                        for i, line in enumerate(lines, 1):
                            if query.lower() in line.lower():
                                results.append(SearchResult(
                                    file_path=file_path,
                                    line_number=i,
                                    content=line.strip(),
                                    context=self._get_context_lines(lines, i-1, 2),
                                    match_type="text"
                                ))
                    except Exception:
                        continue
            
            if not results:
                return f"No matches found for '{query}'"
            
            # Format results
            response = f"Found {len(results)} matches for '{query}':\n\n"
            for result in results[:10]:  # Limit to first 10 results
                response += f"📁 {result.file_path}:{result.line_number}\n"
                response += f"   {result.content}\n\n"
            
            if len(results) > 10:
                response += f"... and {len(results) - 10} more matches"
            
            return response
            
        except Exception as e:
            return f"Search failed: {e}"
    
    async def _find_function(self, function_name: str) -> str:
        """Find function definitions."""
        
        if not self.file_manager:
            return "File manager not available"
        
        try:
            files = await self.file_manager.list_files()
            results = []
            
            # Common function definition patterns
            patterns = [
                rf"def\s+{function_name}\s*\(",  # Python
                rf"function\s+{function_name}\s*\(",  # JavaScript
                rf"{function_name}\s*\([^)]*\)\s*{{",  # C/C++/Java
                rf"async\s+def\s+{function_name}\s*\(",  # Python async
            ]
            
            for file_path in files:
                if file_path.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.c', '.h')):
                    try:
                        content = await self.file_manager.read_file(file_path)
                        lines = content.split('\n')
                        
                        for i, line in enumerate(lines, 1):
                            for pattern in patterns:
                                if re.search(pattern, line, re.IGNORECASE):
                                    results.append(SearchResult(
                                        file_path=file_path,
                                        line_number=i,
                                        content=line.strip(),
                                        context=self._get_context_lines(lines, i-1, 3),
                                        match_type="function"
                                    ))
                    except Exception:
                        continue
            
            if not results:
                return f"No function definitions found for '{function_name}'"
            
            response = f"Found {len(results)} function definitions for '{function_name}':\n\n"
            for result in results:
                response += f"📁 {result.file_path}:{result.line_number}\n"
                response += f"   {result.content}\n\n"
            
            return response
            
        except Exception as e:
            return f"Function search failed: {e}"
    
    async def _find_references(self, symbol: str) -> str:
        """Find references to a symbol."""
        
        if not self.file_manager:
            return "File manager not available"
        
        try:
            files = await self.file_manager.list_files()
            results = []
            
            for file_path in files:
                if file_path.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.c', '.h')):
                    try:
                        content = await self.file_manager.read_file(file_path)
                        lines = content.split('\n')
                        
                        for i, line in enumerate(lines, 1):
                            # Look for symbol usage (not in comments)
                            if symbol in line and not line.strip().startswith('#') and not line.strip().startswith('//'):
                                results.append(SearchResult(
                                    file_path=file_path,
                                    line_number=i,
                                    content=line.strip(),
                                    context=self._get_context_lines(lines, i-1, 1),
                                    match_type="reference"
                                ))
                    except Exception:
                        continue
            
            if not results:
                return f"No references found for '{symbol}'"
            
            response = f"Found {len(results)} references to '{symbol}':\n\n"
            for result in results[:15]:  # Limit results
                response += f"📁 {result.file_path}:{result.line_number}\n"
                response += f"   {result.content}\n\n"
            
            if len(results) > 15:
                response += f"... and {len(results) - 15} more references"
            
            return response
            
        except Exception as e:
            return f"Reference search failed: {e}"
    
    async def _analyze_dependencies(self, file_path: str) -> str:
        """Analyze code dependencies."""
        
        if not self.file_manager:
            return "File manager not available"
        
        try:
            content = await self.file_manager.read_file(file_path)
            lines = content.split('\n')
            
            imports = []
            calls = []
            
            # Find imports and function calls
            for line in lines:
                line = line.strip()
                
                # Python imports
                if line.startswith('import ') or line.startswith('from '):
                    imports.append(line)
                
                # JavaScript imports
                elif 'import' in line and 'from' in line:
                    imports.append(line)
                
                # Function calls (simple pattern)
                elif '(' in line and ')' in line:
                    # Extract potential function calls
                    matches = re.findall(r'(\w+)\s*\(', line)
                    calls.extend(matches)
            
            response = f"Dependencies for {file_path}:\n\n"
            
            if imports:
                response += "📦 Imports:\n"
                for imp in imports[:10]:
                    response += f"   {imp}\n"
                if len(imports) > 10:
                    response += f"   ... and {len(imports) - 10} more\n"
                response += "\n"
            
            if calls:
                unique_calls = list(set(calls))
                response += "🔧 Function calls:\n"
                for call in unique_calls[:15]:
                    response += f"   {call}()\n"
                if len(unique_calls) > 15:
                    response += f"   ... and {len(unique_calls) - 15} more\n"
            
            return response
            
        except Exception as e:
            return f"Dependency analysis failed: {e}"
    
    def _get_context_lines(self, lines: List[str], center: int, radius: int) -> str:
        """Get context lines around a center line."""
        
        start = max(0, center - radius)
        end = min(len(lines), center + radius + 1)
        
        context_lines = []
        for i in range(start, end):
            prefix = ">>> " if i == center else "    "
            context_lines.append(f"{prefix}{lines[i]}")
        
        return '\n'.join(context_lines)
    
    # Function implementations for LLM calls
    async def search_code(self, query: str, file_pattern: str = "*", search_type: str = "text") -> str:
        """Function: Search for code patterns."""
        return await self._search_code(query)
    
    async def find_function(self, function_name: str, language: str = "python") -> str:
        """Function: Find function definitions."""
        return await self._find_function(function_name)
    
    async def find_references(self, symbol: str, symbol_type: str = "function") -> str:
        """Function: Find symbol references."""
        return await self._find_references(symbol)
    
    async def analyze_dependencies(self, file_path: str, analysis_type: str = "imports") -> str:
        """Function: Analyze code dependencies."""
        return await self._analyze_dependencies(file_path)