"""
Context management and RAG (Retrieval-Augmented Generation) system.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from .vector_memory import VectorMemory, MemoryResult


@dataclass
class ContextWindow:
    """Represents a context window for LLM input."""
    content: str
    sources: List[str]
    relevance_score: float
    token_count: int
    metadata: Dict[str, Any]


class ContextManager:
    """Manages context retrieval and assembly for LLM queries."""
    
    def __init__(self, memory: VectorMemory, max_context_tokens: int = 4000):
        self.memory = memory
        self.max_context_tokens = max_context_tokens
        self.context_cache: Dict[str, ContextWindow] = {}
    
    async def get_relevant_context(
        self,
        query: str,
        context_types: List[str] = None,
        max_results: int = 10,
        min_relevance: float = 0.5
    ) -> ContextWindow:
        """Get relevant context for a query."""
        
        # Check cache first
        cache_key = f"{query}:{context_types}:{max_results}"
        if cache_key in self.context_cache:
            return self.context_cache[cache_key]
        
        # Search for relevant content
        filter_metadata = {}
        if context_types:
            filter_metadata["type"] = {"$in": context_types}
        
        results = await self.memory.search(
            query=query,
            limit=max_results,
            filter_metadata=filter_metadata
        )
        
        # Filter by relevance
        relevant_results = [
            result for result in results
            if result.score >= min_relevance
        ]
        
        # Assemble context
        context_window = self._assemble_context(query, relevant_results)
        
        # Cache result
        self.context_cache[cache_key] = context_window
        
        return context_window
    
    def _assemble_context(self, query: str, results: List[MemoryResult]) -> ContextWindow:
        """Assemble context from search results."""
        
        content_parts = []
        sources = []
        total_relevance = 0.0
        token_count = 0
        
        for result in results:
            # Estimate token count (rough approximation)
            result_tokens = len(result.text.split()) * 1.3  # Approximate tokens
            
            if token_count + result_tokens > self.max_context_tokens:
                break
            
            content_parts.append(f"Source: {result.id}\n{result.text}")
            sources.append(result.id)
            total_relevance += result.score
            token_count += result_tokens
        
        avg_relevance = total_relevance / len(results) if results else 0.0
        
        return ContextWindow(
            content="\n\n---\n\n".join(content_parts),
            sources=sources,
            relevance_score=avg_relevance,
            token_count=int(token_count),
            metadata={
                "query": query,
                "result_count": len(results),
                "timestamp": datetime.now().isoformat()
            }
        )
    
    async def store_context(
        self,
        content: str,
        context_type: str,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Store content for future context retrieval."""
        
        metadata = metadata or {}
        metadata.update({
            "type": context_type,
            "stored_at": datetime.now().isoformat()
        })
        
        return await self.memory.store_text(content, metadata)
    
    def clear_cache(self) -> None:
        """Clear context cache."""
        self.context_cache.clear()
    
    async def get_conversation_context(
        self,
        conversation_id: str,
        max_messages: int = 10
    ) -> ContextWindow:
        """Get context from conversation history."""
        
        results = await self.memory.search_by_metadata(
            filter_metadata={"conversation_id": conversation_id},
            limit=max_messages
        )
        
        # Sort by timestamp
        results.sort(key=lambda x: x.metadata.get("timestamp", ""), reverse=True)
        
        return self._assemble_context(f"conversation:{conversation_id}", results)
    
    async def get_code_context(
        self,
        file_path: str,
        function_name: str = None
    ) -> ContextWindow:
        """Get context related to specific code."""
        
        filter_metadata = {"file_path": file_path}
        if function_name:
            filter_metadata["function_name"] = function_name
        
        results = await self.memory.search_by_metadata(
            filter_metadata=filter_metadata,
            limit=5
        )
        
        query = f"code:{file_path}:{function_name}" if function_name else f"code:{file_path}"
        return self._assemble_context(query, results)
    
    async def get_task_context(self, task_id: str) -> ContextWindow:
        """Get context related to a specific task."""
        
        results = await self.memory.search_by_metadata(
            filter_metadata={"task_id": task_id},
            limit=20
        )
        
        return self._assemble_context(f"task:{task_id}", results)