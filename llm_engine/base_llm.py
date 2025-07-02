"""
Abstract base class for LLM interfaces.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, AsyncGenerator
from pydantic import BaseModel


class LLMConfig(BaseModel):
    """Configuration for LLM models."""
    model_name: str
    max_tokens: int = 2048
    temperature: float = 0.3
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    stop_sequences: List[str] = []
    system_prompt: Optional[str] = None


class LLMResponse(BaseModel):
    """Response from LLM model."""
    content: str
    tokens_used: int
    finish_reason: str
    model: str
    metadata: Dict[str, Any] = {}


class BaseLLM(ABC):
    """Abstract base class for LLM interfaces."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.is_connected = False
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the LLM service."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the LLM service."""
        pass
    
    @abstractmethod
    async def generate(
        self, 
        prompt: str, 
        **kwargs
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    async def stream_generate(
        self, 
        prompt: str, 
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream generate a response from the LLM."""
        pass
    
    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """Generate embeddings for text."""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        pass
    
    async def health_check(self) -> bool:
        """Check if the LLM service is healthy."""
        try:
            response = await self.generate("Hello", max_tokens=5)
            return len(response.content) > 0
        except Exception:
            return False
    
    def update_config(self, **kwargs) -> None:
        """Update LLM configuration."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)