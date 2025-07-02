"""
Local embedding models for text vectorization.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class EmbeddingModel(ABC):
    """Abstract base class for embedding models."""
    
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        pass
    
    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """Get embedding dimension."""
        pass


class LocalEmbeddings(EmbeddingModel):
    """Local embedding model using sentence-transformers."""
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str = "auto"
    ):
        self.model_name = model_name
        self.device = device
        self.model: Optional[SentenceTransformer] = None
        self._dimension: Optional[int] = None
        
        # Initialize model
        asyncio.create_task(self._initialize_model())
    
    async def _initialize_model(self) -> None:
        """Initialize the embedding model."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise RuntimeError(
                "sentence-transformers not available. "
                "Install with: pip install sentence-transformers"
            )
        
        try:
            # Run model loading in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None,
                lambda: SentenceTransformer(self.model_name, device=self.device)
            )
            
            # Get embedding dimension
            test_embedding = self.model.encode(["test"])
            self._dimension = len(test_embedding[0])
            
        except Exception as e:
            print(f"Failed to initialize embedding model: {e}")
            # Fallback to simple embeddings
            self.model = None
            self._dimension = 384  # Default dimension
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        if self.model is None:
            return await self._fallback_embedding(text)
        
        try:
            # Run encoding in thread pool
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                lambda: self.model.encode([text])
            )
            return embedding[0].tolist()
            
        except Exception as e:
            print(f"Failed to generate embedding: {e}")
            return await self._fallback_embedding(text)
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if self.model is None:
            return [await self._fallback_embedding(text) for text in texts]
        
        try:
            # Run batch encoding in thread pool
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: self.model.encode(texts)
            )
            return [emb.tolist() for emb in embeddings]
            
        except Exception as e:
            print(f"Failed to generate embeddings: {e}")
            return [await self._fallback_embedding(text) for text in texts]
    
    def get_dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension or 384
    
    async def _fallback_embedding(self, text: str) -> List[float]:
        """Simple fallback embedding using hash-based approach."""
        # This is a very basic fallback - in practice you'd want something better
        import hashlib
        
        # Create a deterministic hash-based embedding
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert to float vector
        embedding = []
        for i in range(0, len(hash_bytes), 4):
            chunk = hash_bytes[i:i+4]
            if len(chunk) == 4:
                value = int.from_bytes(chunk, byteorder='big')
                normalized_value = (value / (2**32 - 1)) * 2 - 1  # Normalize to [-1, 1]
                embedding.append(normalized_value)
        
        # Pad or truncate to desired dimension
        target_dim = self._dimension or 384
        while len(embedding) < target_dim:
            embedding.extend(embedding[:min(len(embedding), target_dim - len(embedding))])
        
        return embedding[:target_dim]


class TFIDFEmbeddings(EmbeddingModel):
    """TF-IDF based embeddings as a lightweight alternative."""
    
    def __init__(self, max_features: int = 1000):
        self.max_features = max_features
        self.vectorizer = None
        self.vocabulary = {}
        self._dimension = max_features
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate TF-IDF embedding for text."""
        if self.vectorizer is None:
            await self._initialize_vectorizer([text])
        
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            
            # Transform text
            vector = self.vectorizer.transform([text])
            return vector.toarray()[0].tolist()
            
        except ImportError:
            # Fallback to simple word count embedding
            return await self._simple_word_embedding(text)
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate TF-IDF embeddings for multiple texts."""
        if self.vectorizer is None:
            await self._initialize_vectorizer(texts)
        
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            
            # Transform texts
            vectors = self.vectorizer.transform(texts)
            return vectors.toarray().tolist()
            
        except ImportError:
            # Fallback to simple embeddings
            return [await self._simple_word_embedding(text) for text in texts]
    
    def get_dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension
    
    async def _initialize_vectorizer(self, texts: List[str]) -> None:
        """Initialize TF-IDF vectorizer."""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            
            self.vectorizer = TfidfVectorizer(
                max_features=self.max_features,
                stop_words='english',
                lowercase=True
            )
            
            # Fit on provided texts
            self.vectorizer.fit(texts)
            
        except ImportError:
            print("scikit-learn not available, using simple word embeddings")
            self.vectorizer = None
    
    async def _simple_word_embedding(self, text: str) -> List[float]:
        """Simple word-based embedding fallback."""
        words = text.lower().split()
        
        # Create a simple bag-of-words representation
        embedding = [0.0] * self._dimension
        
        for i, word in enumerate(words[:self._dimension]):
            # Simple hash-based position
            pos = hash(word) % self._dimension
            embedding[pos] += 1.0
        
        # Normalize
        total = sum(embedding)
        if total > 0:
            embedding = [x / total for x in embedding]
        
        return embedding


class OllamaEmbeddings(EmbeddingModel):
    """Embeddings using Ollama's embedding models."""
    
    def __init__(
        self,
        model_name: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434"
    ):
        self.model_name = model_name
        self.base_url = base_url.rstrip('/')
        self._dimension = 768  # Default for most embedding models
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding using Ollama."""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/embeddings",
                    json={
                        "model": self.model_name,
                        "prompt": text
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("embedding", [])
                    else:
                        raise RuntimeError(f"Ollama API error: {response.status}")
                        
        except Exception as e:
            print(f"Failed to get Ollama embedding: {e}")
            # Fallback to local embedding
            local_embeddings = LocalEmbeddings()
            return await local_embeddings.embed_text(text)
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = []
        for text in texts:
            embedding = await self.embed_text(text)
            embeddings.append(embedding)
        return embeddings
    
    def get_dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension


def get_embedding_model(
    model_type: str = "sentence_transformers",
    **kwargs
) -> EmbeddingModel:
    """Factory function to get embedding model."""
    
    if model_type == "sentence_transformers":
        return LocalEmbeddings(**kwargs)
    elif model_type == "tfidf":
        return TFIDFEmbeddings(**kwargs)
    elif model_type == "ollama":
        return OllamaEmbeddings(**kwargs)
    else:
        raise ValueError(f"Unknown embedding model type: {model_type}")