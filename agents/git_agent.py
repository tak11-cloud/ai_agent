"""
Git Agent - Handles version control operations.
"""

from agents.base_agent import BaseAgent, AgentThought
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_engine import FunctionSchema


class GitAgent(BaseAgent):
    """Agent responsible for Git version control operations."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role_description = """
You are a Git expert responsible for version control operations. You excel at:
- Managing Git repositories and branches
- Creating meaningful commits and commit messages
- Handling merges and conflicts
- Managing remote repositories
- Following Git best practices
"""
        self.add_capability("version_control")
        self.add_capability("branch_management")
        self.add_capability("commit_management")
        self.add_capability("merge_operations")
    
    def _setup_functions(self) -> None:
        """Setup git-specific functions."""
        
        # Git commit function
        commit_schema = FunctionSchema(
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
                },
                "add_all": {
                    "type": "boolean",
                    "description": "Whether to add all changes"
                }
            },
            required=["message"]
        )
        
        self.function_caller.register_function(
            self._git_commit,
            commit_schema
        )
    
    async def _think(self, observation: str) -> AgentThought:
        """Generate git operation thoughts."""
        
        # Get relevant context from memory
        context = await self.get_relevant_context(observation)
        context_str = "\n".join(context) if context else "No relevant context found."
        
        # Build git prompt
        prompt = f"""
You are a Git expert. Analyze this version control request:

REQUEST: {observation}

CONTEXT: {context_str}

Determine what Git operations are needed and provide:
1. The specific Git commands to run
2. Appropriate commit messages if committing
3. Any branch operations needed
4. Safety considerations

Provide your analysis and the Git action to take.
"""
        
        # Get LLM response
        response = await self.llm.generate(prompt)
        
        return AgentThought(
            observation=observation,
            thought=response.content,
            action="git_operation",
            action_input={"operation": observation}
        )
    
    async def _act(self, thought: AgentThought) -> str:
        """Execute git action."""
        
        # Use function calling
        function_calls = self.function_caller.parse_function_calls(thought.thought)
        if function_calls:
            results = await self.function_caller.execute_function_calls(function_calls)
            return self.function_caller.format_function_results(results)
        else:
            return f"Git analysis: {thought.thought}"
    
    async def _git_commit(
        self,
        message: str,
        files: list = None,
        add_all: bool = True
    ) -> str:
        """Function to commit changes."""
        
        # This would integrate with actual Git operations
        # For now, return a simulation
        
        if add_all:
            files_str = "all changes"
        elif files:
            files_str = f"files: {', '.join(files)}"
        else:
            files_str = "staged changes"
        
        result = f"Committed {files_str} with message: '{message}'"
        
        # Store in memory
        await self.memory.store_text(
            text=f"Git commit: {message}\nFiles: {files_str}",
            metadata={
                "type": "git_commit",
                "agent": self.name,
                "message": message
            }
        )
        
        return result


class MemoryAgent(BaseAgent):
    """Agent responsible for memory and context management."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role_description = """
You are a memory and context expert responsible for managing information storage and retrieval. You excel at:
- Storing and organizing information efficiently
- Retrieving relevant context for tasks
- Managing conversation history
- Summarizing and indexing content
"""
        self.add_capability("memory_management")
        self.add_capability("context_retrieval")
        self.add_capability("information_organization")
    
    def _setup_functions(self) -> None:
        """Setup memory-specific functions."""
        pass
    
    async def _think(self, observation: str) -> AgentThought:
        """Generate memory management thoughts."""
        
        prompt = f"""
You are a memory management expert. Analyze this request:

REQUEST: {observation}

Determine what memory operations are needed:
1. Should information be stored?
2. What context should be retrieved?
3. How should information be organized?
4. What summaries are needed?

Provide your analysis.
"""
        
        response = await self.llm.generate(prompt)
        
        return AgentThought(
            observation=observation,
            thought=response.content,
            action="memory_operation",
            action_input={"operation": observation}
        )
    
    async def _act(self, thought: AgentThought) -> str:
        """Execute memory action."""
        return f"Memory analysis: {thought.thought}"


class SearchAgent(BaseAgent):
    """Agent responsible for code search and analysis."""
    
    def __init__(self, file_manager=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file_manager = file_manager
        self.role_description = """
You are a code search and analysis expert. You excel at:
- Searching through codebases efficiently
- Finding relevant code patterns and functions
- Analyzing code structure and dependencies
- Identifying code relationships and usage
"""
        self.add_capability("code_search")
        self.add_capability("pattern_matching")
        self.add_capability("code_analysis")
    
    def _setup_functions(self) -> None:
        """Setup search-specific functions."""
        pass
    
    async def _think(self, observation: str) -> AgentThought:
        """Generate search thoughts."""
        
        prompt = f"""
You are a code search expert. Analyze this search request:

REQUEST: {observation}

Determine:
1. What should be searched for?
2. Which files or directories to search?
3. What search patterns to use?
4. How to analyze the results?

Provide your search strategy.
"""
        
        response = await self.llm.generate(prompt)
        
        return AgentThought(
            observation=observation,
            thought=response.content,
            action="search_operation",
            action_input={"query": observation}
        )
    
    async def _act(self, thought: AgentThought) -> str:
        """Execute search action."""
        
        if self.file_manager:
            # Perform actual search
            try:
                query = thought.action_input.get("query", "")
                results = await self.file_manager.search_in_files(
                    pattern=query,
                    directory=".",
                    file_pattern="*.py",
                    case_sensitive=False
                )
                
                if results:
                    search_summary = f"Found {len(results)} files with matches:\n"
                    for result in results[:5]:  # Limit to first 5 results
                        search_summary += f"- {result['file']}: {result['total_matches']} matches\n"
                    return search_summary
                else:
                    return f"No matches found for: {query}"
                    
            except Exception as e:
                return f"Search error: {str(e)}"
        else:
            return f"Search analysis: {thought.thought}"