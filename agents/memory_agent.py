"""
Memory Agent - Manages memory storage and retrieval.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from agents.base_agent import BaseAgent, AgentThought
from llm_engine import FunctionSchema
from memory.vector_memory import VectorMemory
from memory.context_manager import ContextManager


@dataclass
class MemoryQuery:
    """Represents a memory query."""
    query: str
    context_types: List[str]
    max_results: int = 10
    min_relevance: float = 0.5


class MemoryAgent(BaseAgent):
    """Agent responsible for memory management and context retrieval."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role_description = "Memory and context management expert"
        self.add_capability("memory_management")
        self.add_capability("context_retrieval")
        self.add_capability("information_organization")
        
        # Initialize memory components
        self.memory: Optional[VectorMemory] = None
        self.context_manager: Optional[ContextManager] = None
    
    def _setup_functions(self):
        """Setup memory-specific functions."""
        
        self.add_function(FunctionSchema(
            name="store_memory",
            description="Store information in memory",
            parameters={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Content to store"},
                    "context_type": {"type": "string", "description": "Type of content"},
                    "metadata": {"type": "object", "description": "Additional metadata"}
                },
                "required": ["content", "context_type"]
            }
        ))
        
        self.add_function(FunctionSchema(
            name="search_memory",
            description="Search for relevant information in memory",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "context_types": {"type": "array", "items": {"type": "string"}},
                    "max_results": {"type": "integer", "default": 10}
                },
                "required": ["query"]
            }
        ))
        
        self.add_function(FunctionSchema(
            name="get_context",
            description="Get relevant context for a task",
            parameters={
                "type": "object",
                "properties": {
                    "task_description": {"type": "string", "description": "Description of the task"},
                    "context_types": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["task_description"]
            }
        ))
    
    async def _think(self, observation: str) -> AgentThought:
        """Think about memory operations."""
        
        # Analyze what memory operations are needed
        if "store" in observation.lower() or "save" in observation.lower():
            action_type = "store_information"
            reasoning = "Need to store information in memory for future retrieval"
        elif "search" in observation.lower() or "find" in observation.lower():
            action_type = "search_memory"
            reasoning = "Need to search memory for relevant information"
        elif "context" in observation.lower():
            action_type = "get_context"
            reasoning = "Need to retrieve relevant context for the task"
        else:
            action_type = "analyze_memory_needs"
            reasoning = "Analyzing what memory operations are needed"
        
        return AgentThought(
            observation=observation,
            reasoning=reasoning,
            action_type=action_type,
            confidence=0.8
        )
    
    async def _act(self, thought: AgentThought) -> str:
        """Execute memory operations."""
        
        if thought.action_type == "store_information":
            return await self._store_information(thought.observation)
        elif thought.action_type == "search_memory":
            return await self._search_memory(thought.observation)
        elif thought.action_type == "get_context":
            return await self._get_context(thought.observation)
        else:
            return "Memory agent ready to help with storage and retrieval operations."
    
    async def _store_information(self, content: str) -> str:
        """Store information in memory."""
        
        if not self.memory:
            return "Memory system not available"
        
        try:
            # Extract metadata from content
            metadata = {
                "source": "memory_agent",
                "type": "general_information"
            }
            
            # Store in memory
            doc_id = await self.memory.store_text(content, metadata)
            
            return f"Information stored successfully with ID: {doc_id}"
            
        except Exception as e:
            return f"Failed to store information: {e}"
    
    async def _search_memory(self, query: str) -> str:
        """Search memory for relevant information."""
        
        if not self.memory:
            return "Memory system not available"
        
        try:
            # Search memory
            results = await self.memory.search(query, limit=5)
            
            if not results:
                return "No relevant information found in memory"
            
            # Format results
            response = "Found relevant information:\n\n"
            for i, result in enumerate(results, 1):
                response += f"{i}. {result.text[:200]}...\n"
                response += f"   Relevance: {result.score:.2f}\n\n"
            
            return response
            
        except Exception as e:
            return f"Failed to search memory: {e}"
    
    async def _get_context(self, task_description: str) -> str:
        """Get relevant context for a task."""
        
        if not self.context_manager:
            return "Context manager not available"
        
        try:
            # Get relevant context
            context = await self.context_manager.get_relevant_context(
                query=task_description,
                max_results=5
            )
            
            if not context.content:
                return "No relevant context found"
            
            return f"Relevant context:\n\n{context.content}"
            
        except Exception as e:
            return f"Failed to get context: {e}"
    
    async def store_memory(self, content: str, context_type: str, metadata: Dict[str, Any] = None) -> str:
        """Function: Store information in memory."""
        
        if not self.memory:
            return "Memory system not available"
        
        metadata = metadata or {}
        metadata.update({
            "type": context_type,
            "source": "memory_agent"
        })
        
        doc_id = await self.memory.store_text(content, metadata)
        return f"Stored with ID: {doc_id}"
    
    async def search_memory(self, query: str, context_types: List[str] = None, max_results: int = 10) -> str:
        """Function: Search memory for information."""
        
        if not self.memory:
            return "Memory system not available"
        
        filter_metadata = {}
        if context_types:
            filter_metadata["type"] = {"$in": context_types}
        
        results = await self.memory.search(
            query=query,
            limit=max_results,
            filter_metadata=filter_metadata
        )
        
        if not results:
            return "No results found"
        
        response = f"Found {len(results)} results:\n\n"
        for i, result in enumerate(results, 1):
            response += f"{i}. {result.text[:150]}...\n"
            response += f"   Score: {result.score:.2f}\n\n"
        
        return response
    
    async def get_context(self, task_description: str, context_types: List[str] = None) -> str:
        """Function: Get relevant context for a task."""
        
        if not self.context_manager:
            return "Context manager not available"
        
        context = await self.context_manager.get_relevant_context(
            query=task_description,
            context_types=context_types,
            max_results=5
        )
        
        return context.content or "No relevant context found"