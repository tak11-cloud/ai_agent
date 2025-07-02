"""
LLM Engine Module

Provides interfaces to local LLM models via Ollama and llama.cpp.
Supports ReAct prompting, function calling, and dynamic prompt assembly.
"""

from .base_llm import BaseLLM, LLMConfig, LLMResponse
from .ollama_client import OllamaClient
from .llamacpp_client import LlamaCppClient
from .prompt_builder import PromptBuilder, ReActPrompt
from .function_calling import FunctionCaller, FunctionSchema

__all__ = [
    "BaseLLM",
    "LLMConfig",
    "LLMResponse",
    "OllamaClient", 
    "LlamaCppClient",
    "PromptBuilder",
    "ReActPrompt",
    "FunctionCaller",
    "FunctionSchema"
]