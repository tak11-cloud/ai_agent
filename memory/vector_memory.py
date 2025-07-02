"""
Vector memory system using ChromaDB for semantic search and storage.
"""

import uuid
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

from .embeddings import LocalEmbeddings


@dataclass
class MemoryResult:
    """Result from memory search."""
    id: str
    text: str
    metadata: Dict[str, Any]
    score: float
    distance: float


class VectorMemory:
    """Vector-based memory system using ChromaDB."""
    
    def __init__(
        self,
        collection_name: str = "agent_memory",
        persist_directory: str = "./data/memory",
        embedding_model: Optional[LocalEmbeddings] = None
    ):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.embedding_model = embedding_model or LocalEmbeddings()
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Create or get collection
        self.collection = self._get_or_create_collection()
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    def _get_or_create_collection(self):
        """Get or create ChromaDB collection."""
        try:
            # Try to get existing collection
            return self.client.get_collection(
                name=self.collection_name,
                embedding_function=self._get_embedding_function()
            )
        except Exception as e:
            # Create new collection
            try:
                return self.client.create_collection(
                    name=self.collection_name,
                    embedding_function=self._get_embedding_function(),
                    metadata={"description": "Agent memory storage"}
                )
            except Exception as create_error:
                print(f"Warning: Failed to create collection {self.collection_name}: {create_error}")
                # Return None for testing - methods will handle gracefully
                return None
    
    def _get_embedding_function(self):
        """Get embedding function for ChromaDB."""
        # Use custom embedding function that wraps our local embeddings
        class LocalEmbeddingFunction(embedding_functions.EmbeddingFunction):
            def __init__(self, embedding_model):
                self.embedding_model = embedding_model
            
            def __call__(self, input_texts):
                # Convert async to sync for ChromaDB compatibility
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    embeddings = []
                    for text in input_texts:
                        embedding = loop.run_until_complete(
                            self.embedding_model.embed_text(text)
                        )
                        embeddings.append(embedding)
                    return embeddings
                finally:
                    loop.close()
        
        return LocalEmbeddingFunction(self.embedding_model)
    
    async def store_text(
        self,
        text: str,
        metadata: Dict[str, Any] = None,
        doc_id: str = None
    ) -> str:
        """Store text in vector memory."""
        
        async with self._lock:
            # Check if collection is available
            if self.collection is None:
                print("Warning: Collection not available, skipping storage")
                return str(uuid.uuid4())
            
            # Generate ID if not provided
            if doc_id is None:
                doc_id = str(uuid.uuid4())
            
            # Add timestamp to metadata
            metadata = metadata or {}
            metadata.update({
                "timestamp": datetime.now().isoformat(),
                "text_length": len(text)
            })
            
            try:
                # Add to collection
                self.collection.add(
                    documents=[text],
                    metadatas=[metadata],
                    ids=[doc_id]
                )
                
                return doc_id
                
            except Exception as e:
                raise RuntimeError(f"Failed to store text: {e}")
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        filter_metadata: Dict[str, Any] = None
    ) -> List[MemoryResult]:
        """Search for similar texts."""
        
        async with self._lock:
            try:
                # Perform similarity search
                results = self.collection.query(
                    query_texts=[query],
                    n_results=limit,
                    where=filter_metadata
                )
                
                # Convert to MemoryResult objects
                memory_results = []
                
                if results['documents'] and results['documents'][0]:
                    for i in range(len(results['documents'][0])):
                        memory_results.append(MemoryResult(
                            id=results['ids'][0][i],
                            text=results['documents'][0][i],
                            metadata=results['metadatas'][0][i] if results['metadatas'][0] else {},
                            score=1.0 - results['distances'][0][i],  # Convert distance to similarity
                            distance=results['distances'][0][i]
                        ))
                
                return memory_results
                
            except Exception as e:
                raise RuntimeError(f"Failed to search memory: {e}")
    
    async def get_by_id(self, doc_id: str) -> Optional[MemoryResult]:
        """Get document by ID."""
        
        async with self._lock:
            try:
                results = self.collection.get(
                    ids=[doc_id],
                    include=["documents", "metadatas"]
                )
                
                if results['documents']:
                    return MemoryResult(
                        id=doc_id,
                        text=results['documents'][0],
                        metadata=results['metadatas'][0] if results['metadatas'] else {},
                        score=1.0,
                        distance=0.0
                    )
                
                return None
                
            except Exception as e:
                raise RuntimeError(f"Failed to get document: {e}")
    
    async def update_text(
        self,
        doc_id: str,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Update existing document."""
        
        async with self._lock:
            try:
                # Update metadata with timestamp
                metadata = metadata or {}
                metadata.update({
                    "updated_at": datetime.now().isoformat(),
                    "text_length": len(text)
                })
                
                self.collection.update(
                    ids=[doc_id],
                    documents=[text],
                    metadatas=[metadata]
                )
                
                return True
                
            except Exception as e:
                print(f"Failed to update document: {e}")
                return False
    
    async def delete(self, doc_id: str) -> bool:
        """Delete document by ID."""
        
        async with self._lock:
            try:
                self.collection.delete(ids=[doc_id])
                return True
                
            except Exception as e:
                print(f"Failed to delete document: {e}")
                return False
    
    async def get_all_metadata(self) -> List[Dict[str, Any]]:
        """Get metadata for all documents."""
        
        async with self._lock:
            try:
                results = self.collection.get(include=["metadatas"])
                return results['metadatas'] if results['metadatas'] else []
                
            except Exception as e:
                print(f"Failed to get metadata: {e}")
                return []
    
    async def search_by_metadata(
        self,
        filter_metadata: Dict[str, Any],
        limit: int = 10
    ) -> List[MemoryResult]:
        """Search documents by metadata filters."""
        
        async with self._lock:
            try:
                results = self.collection.get(
                    where=filter_metadata,
                    limit=limit,
                    include=["documents", "metadatas"]
                )
                
                memory_results = []
                
                if results['documents']:
                    for i in range(len(results['documents'])):
                        memory_results.append(MemoryResult(
                            id=results['ids'][i],
                            text=results['documents'][i],
                            metadata=results['metadatas'][i] if results['metadatas'] else {},
                            score=1.0,
                            distance=0.0
                        ))
                
                return memory_results
                
            except Exception as e:
                raise RuntimeError(f"Failed to search by metadata: {e}")
    
    async def get_recent(
        self,
        limit: int = 10,
        hours: int = 24
    ) -> List[MemoryResult]:
        """Get recent documents."""
        
        # Calculate cutoff time
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        
        # Search for recent documents
        # Note: This is a simplified implementation
        # In practice, you'd want to filter by timestamp in metadata
        results = await self.search_by_metadata(
            filter_metadata={},  # Would need proper timestamp filtering
            limit=limit
        )
        
        return results
    
    async def clear_collection(self) -> bool:
        """Clear all documents from collection."""
        
        async with self._lock:
            try:
                # Delete the collection and recreate it
                self.client.delete_collection(self.collection_name)
                self.collection = self._get_or_create_collection()
                return True
                
            except Exception as e:
                print(f"Failed to clear collection: {e}")
                return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        
        async with self._lock:
            try:
                count = self.collection.count()
                
                return {
                    "total_documents": count,
                    "collection_name": self.collection_name,
                    "persist_directory": self.persist_directory
                }
                
            except Exception as e:
                return {
                    "error": str(e),
                    "total_documents": 0,
                    "collection_name": self.collection_name,
                    "persist_directory": self.persist_directory
                }
    
    async def semantic_search_with_context(
        self,
        query: str,
        context_window: int = 3,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search with surrounding context."""
        
        # Get initial results
        results = await self.search(query, limit=limit)
        
        # For each result, try to get surrounding context
        enhanced_results = []
        
        for result in results:
            enhanced_result = {
                "main_result": result,
                "context_before": [],
                "context_after": []
            }
            
            # This would require storing sequence information
            # For now, just return the main results
            enhanced_results.append(enhanced_result)
        
        return enhanced_results