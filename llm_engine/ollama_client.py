"""
Ollama client for local LLM inference via REST API.
"""

import json
import aiohttp
from typing import List, AsyncGenerator, Dict, Any
from .base_llm import BaseLLM, LLMConfig, LLMResponse


class OllamaClient(BaseLLM):
    """Client for Ollama REST API."""
    
    def __init__(self, config: LLMConfig, base_url: str = "http://localhost:11434"):
        super().__init__(config)
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def connect(self) -> bool:
        """Connect to Ollama service."""
        try:
            self.session = aiohttp.ClientSession()
            
            # Test connection
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    self.is_connected = True
                    return True
                return False
        except Exception as e:
            print(f"Failed to connect to Ollama: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Ollama service."""
        if self.session:
            await self.session.close()
            self.session = None
        self.is_connected = False
    
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate response using Ollama."""
        if not self.session:
            raise RuntimeError("Not connected to Ollama")
        
        # Merge config with kwargs
        params = {
            "model": self.config.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": kwargs.get("max_tokens", self.config.max_tokens),
                "temperature": kwargs.get("temperature", self.config.temperature),
                "top_p": kwargs.get("top_p", self.config.top_p),
                "top_k": kwargs.get("top_k", self.config.top_k),
                "repeat_penalty": kwargs.get("repeat_penalty", self.config.repeat_penalty),
                "stop": kwargs.get("stop_sequences", self.config.stop_sequences),
            }
        }
        
        if self.config.system_prompt:
            params["system"] = self.config.system_prompt
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/generate",
                json=params,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"Ollama API error: {response.status}")
                
                result = await response.json()
                
                return LLMResponse(
                    content=result.get("response", ""),
                    tokens_used=result.get("eval_count", 0),
                    finish_reason=result.get("done_reason", "completed"),
                    model=self.config.model_name,
                    metadata={
                        "total_duration": result.get("total_duration", 0),
                        "load_duration": result.get("load_duration", 0),
                        "prompt_eval_count": result.get("prompt_eval_count", 0),
                        "eval_duration": result.get("eval_duration", 0)
                    }
                )
        except Exception as e:
            raise RuntimeError(f"Failed to generate response: {e}")
    
    async def stream_generate(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Stream generate response using Ollama."""
        if not self.session:
            raise RuntimeError("Not connected to Ollama")
        
        params = {
            "model": self.config.model_name,
            "prompt": prompt,
            "stream": True,
            "options": {
                "num_predict": kwargs.get("max_tokens", self.config.max_tokens),
                "temperature": kwargs.get("temperature", self.config.temperature),
                "top_p": kwargs.get("top_p", self.config.top_p),
                "top_k": kwargs.get("top_k", self.config.top_k),
                "repeat_penalty": kwargs.get("repeat_penalty", self.config.repeat_penalty),
                "stop": kwargs.get("stop_sequences", self.config.stop_sequences),
            }
        }
        
        if self.config.system_prompt:
            params["system"] = self.config.system_prompt
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/generate",
                json=params,
                timeout=aiohttp.ClientTimeout(total=300)
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"Ollama API error: {response.status}")
                
                async for line in response.content:
                    if line:
                        try:
                            data = json.loads(line.decode('utf-8'))
                            if "response" in data:
                                yield data["response"]
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            raise RuntimeError(f"Failed to stream generate: {e}")
    
    async def embed(self, text: str) -> List[float]:
        """Generate embeddings using Ollama."""
        if not self.session:
            raise RuntimeError("Not connected to Ollama")
        
        params = {
            "model": self.config.model_name,
            "prompt": text
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/embeddings",
                json=params
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"Ollama embeddings API error: {response.status}")
                
                result = await response.json()
                return result.get("embedding", [])
        except Exception as e:
            raise RuntimeError(f"Failed to generate embeddings: {e}")
    
    def get_available_models(self) -> List[str]:
        """Get available models from Ollama."""
        # This would need to be implemented as a sync method or called differently
        # For now, return common models
        return [
            "mixtral:8x7b",
            "llama3:8b",
            "llama3:70b", 
            "openchat:7b",
            "codellama:7b",
            "codellama:13b",
            "mistral:7b"
        ]
    
    async def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry."""
        if not self.session:
            raise RuntimeError("Not connected to Ollama")
        
        params = {"name": model_name}
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/pull",
                json=params,
                timeout=aiohttp.ClientTimeout(total=1800)  # 30 minutes for model download
            ) as response:
                if response.status != 200:
                    return False
                
                # Stream the pull progress
                async for line in response.content:
                    if line:
                        try:
                            data = json.loads(line.decode('utf-8'))
                            if data.get("status") == "success":
                                return True
                        except json.JSONDecodeError:
                            continue
                return True
        except Exception as e:
            print(f"Failed to pull model {model_name}: {e}")
            return False