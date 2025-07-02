"""
Global settings and configuration management.
"""

import os
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class LLMConfig(BaseModel):
    """LLM configuration."""
    provider: str = "ollama"  # ollama, llamacpp
    model_name: str = "mixtral:8x7b"
    base_url: str = "http://localhost:11434"
    max_tokens: int = 2048
    temperature: float = 0.3
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    stop_sequences: List[str] = []
    system_prompt: Optional[str] = None


class AgentConfig(BaseModel):
    """Individual agent configuration."""
    name: str
    enabled: bool = True
    max_iterations: int = 10
    timeout: int = 300
    memory_limit: int = 1000
    custom_settings: Dict[str, Any] = {}


class MemoryConfig(BaseModel):
    """Memory system configuration."""
    provider: str = "chromadb"
    persist_directory: str = "./data/memory"
    collection_name: str = "agent_memory"
    embedding_model: str = "sentence_transformers"
    embedding_model_name: str = "all-MiniLM-L6-v2"
    max_memory_size: int = 10000
    cleanup_threshold: float = 0.8


class ExecutorConfig(BaseModel):
    """Executor configuration."""
    use_sandbox: bool = True
    sandbox_type: str = "docker"  # docker, firecracker, none
    working_directory: str = "/tmp/agent_workspace"
    max_execution_time: int = 300
    max_output_size: int = 1024 * 1024  # 1MB
    allow_network: bool = True
    allow_system_modification: bool = False


class SecurityConfig(BaseModel):
    """Security configuration."""
    enable_command_filtering: bool = True
    enable_path_restrictions: bool = True
    enable_resource_limits: bool = True
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    max_files_per_operation: int = 100
    allowed_file_extensions: List[str] = [
        ".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".go", ".rs",
        ".rb", ".php", ".sh", ".sql", ".html", ".css", ".json", ".yaml",
        ".yml", ".xml", ".md", ".txt", ".log", ".conf", ".cfg"
    ]


class UIConfig(BaseModel):
    """UI configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    enable_cors: bool = True
    enable_websocket: bool = True
    static_files_directory: str = "./ui/frontend/dist"
    api_prefix: str = "/api/v1"


class Settings(BaseSettings):
    """Global application settings."""
    
    # Application info
    app_name: str = "GodDevX - Autonomous Developer Assistant"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # LLM settings
    llm: LLMConfig = LLMConfig()
    
    # Agent settings
    agents: Dict[str, AgentConfig] = {
        "planner": AgentConfig(name="planner", max_iterations=5),
        "coder": AgentConfig(name="coder", max_iterations=10),
        "terminal": AgentConfig(name="terminal", max_iterations=3),
        "debugger": AgentConfig(name="debugger", max_iterations=8),
        "git": AgentConfig(name="git", max_iterations=3),
        "memory": AgentConfig(name="memory", max_iterations=2),
        "search": AgentConfig(name="search", max_iterations=5)
    }
    
    # Memory settings
    memory: MemoryConfig = MemoryConfig()
    
    # Executor settings
    executor: ExecutorConfig = ExecutorConfig()
    
    # Security settings
    security: SecurityConfig = SecurityConfig()
    
    # UI settings
    ui: UIConfig = UIConfig()
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = "./logs/agent.log"
    
    # Data directories
    data_directory: str = "./data"
    logs_directory: str = "./logs"
    temp_directory: str = "/tmp/agent_temp"
    
    # Feature flags
    enable_self_healing: bool = True
    enable_memory_persistence: bool = True
    enable_conversation_history: bool = True
    enable_code_analysis: bool = True
    enable_git_integration: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "AGENT_"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Create directories
        os.makedirs(self.data_directory, exist_ok=True)
        os.makedirs(self.logs_directory, exist_ok=True)
        os.makedirs(self.temp_directory, exist_ok=True)
        os.makedirs(self.memory.persist_directory, exist_ok=True)
        os.makedirs(self.executor.working_directory, exist_ok=True)
    
    def get_agent_config(self, agent_name: str) -> Optional[AgentConfig]:
        """Get configuration for a specific agent."""
        return self.agents.get(agent_name)
    
    def update_agent_config(self, agent_name: str, config: AgentConfig) -> None:
        """Update configuration for a specific agent."""
        self.agents[agent_name] = config
    
    def get_llm_config_dict(self) -> Dict[str, Any]:
        """Get LLM configuration as dictionary."""
        return self.llm.model_dump()
    
    def get_memory_config_dict(self) -> Dict[str, Any]:
        """Get memory configuration as dictionary."""
        return self.memory.model_dump()
    
    def is_agent_enabled(self, agent_name: str) -> bool:
        """Check if an agent is enabled."""
        config = self.get_agent_config(agent_name)
        return config.enabled if config else False
    
    def get_enabled_agents(self) -> List[str]:
        """Get list of enabled agents."""
        return [
            name for name, config in self.agents.items()
            if config.enabled
        ]
    
    def validate_settings(self) -> List[str]:
        """Validate settings and return any errors."""
        errors = []
        
        # Check required directories
        required_dirs = [
            self.data_directory,
            self.logs_directory,
            self.memory.persist_directory,
            self.executor.working_directory
        ]
        
        for directory in required_dirs:
            if not os.path.exists(directory):
                try:
                    os.makedirs(directory, exist_ok=True)
                except Exception as e:
                    errors.append(f"Cannot create directory {directory}: {e}")
        
        # Check LLM configuration
        if self.llm.provider not in ["ollama", "llamacpp"]:
            errors.append(f"Invalid LLM provider: {self.llm.provider}")
        
        if self.llm.max_tokens <= 0:
            errors.append("LLM max_tokens must be positive")
        
        if not (0.0 <= self.llm.temperature <= 2.0):
            errors.append("LLM temperature must be between 0.0 and 2.0")
        
        # Check memory configuration
        if self.memory.max_memory_size <= 0:
            errors.append("Memory max_memory_size must be positive")
        
        # Check executor configuration
        if self.executor.max_execution_time <= 0:
            errors.append("Executor max_execution_time must be positive")
        
        # Check security configuration
        if self.security.max_file_size <= 0:
            errors.append("Security max_file_size must be positive")
        
        return errors


# Global settings instance
settings = Settings()