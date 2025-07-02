# 🧠 GodDevX - Autonomous Developer Assistant Platform

## 📦 PROJECT STRUCTURE

```
ai_agent/
├── main.py                          # Main entry point and agent runtime loop
├── requirements.txt                 # Python dependencies
├── docker-compose.yml              # Docker setup for sandboxing
├── Dockerfile                      # Container for execution environment
├── config/
│   ├── __init__.py
│   ├── settings.py                 # Global configuration
│   ├── agent_roles.yaml           # Agent role definitions
│   └── prompts/                    # Prompt templates
│       ├── react_template.txt
│       ├── planner_prompts.txt
│       └── coder_prompts.txt
├── agents/
│   ├── __init__.py
│   ├── base_agent.py              # Abstract base agent class
│   ├── planner_agent.py           # Task decomposition and planning
│   ├── coder_agent.py             # Code generation and modification
│   ├── terminal_agent.py          # Command execution
│   ├── debugger_agent.py          # Error detection and fixing
│   ├── git_agent.py               # Version control operations
│   ├── memory_agent.py            # Context and memory management
│   ├── search_agent.py            # Code search and analysis
│   └── orchestrator.py            # Multi-agent coordination
├── llm_engine/
│   ├── __init__.py
│   ├── base_llm.py                # Abstract LLM interface
│   ├── ollama_client.py           # Ollama REST API client
│   ├── llamacpp_client.py         # llama.cpp bindings
│   ├── prompt_builder.py          # ReAct + ChatML prompt assembly
│   └── function_calling.py        # JSON schema function calling
├── memory/
│   ├── __init__.py
│   ├── vector_memory.py           # ChromaDB vector storage
│   ├── embeddings.py              # Local embedding models
│   ├── context_manager.py         # RAG and context retrieval
│   └── conversation_memory.py     # Chat history management
├── executor/
│   ├── __init__.py
│   ├── terminal_runner.py         # Sandboxed command execution
│   ├── docker_sandbox.py          # Docker container management
│   └── security_manager.py        # Permission and safety checks
├── tools/
│   ├── __init__.py
│   ├── code_parser.py             # Tree-sitter AST parsing
│   ├── file_manager.py            # File operations and diff tracking
│   ├── git_tools.py               # Git integration via GitPython
│   ├── test_runner.py             # Test execution and analysis
│   └── error_analyzer.py          # Error parsing and diagnosis
├── ui/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI application
│   │   ├── websocket.py           # WebSocket for real-time chat
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── chat.py            # Chat endpoints
│   │       ├── agents.py          # Agent status endpoints
│   │       └── files.py           # File management endpoints
│   └── frontend/
│       ├── package.json
│       ├── src/
│       │   ├── App.tsx            # Main React application
│       │   ├── components/
│       │   │   ├── Chat.tsx       # Chat interface
│       │   │   ├── AgentStatus.tsx # Agent monitoring
│       │   │   └── FileExplorer.tsx # File browser
│       │   └── hooks/
│       │       └── useWebSocket.ts # WebSocket hook
│       └── public/
├── examples/
│   ├── __init__.py
│   ├── bug_fix_workflow.py        # Example: automated bug fixing
│   ├── feature_development.py     # Example: feature implementation
│   └── test_generation.py         # Example: test writing
└── tests/
    ├── __init__.py
    ├── test_agents/
    ├── test_llm_engine/
    ├── test_memory/
    ├── test_executor/
    └── test_tools/
```

## 🧠 AGENT ARCHITECTURE

### Core Agents
- **PlannerAgent**: Breaks down complex tasks into actionable steps
- **CoderAgent**: Generates, modifies, and refactors code
- **TerminalAgent**: Executes commands in sandboxed environment
- **DebuggerAgent**: Analyzes errors and implements fixes
- **GitAgent**: Manages version control operations
- **MemoryAgent**: Handles context retrieval and storage
- **SearchAgent**: Searches and analyzes codebase

### Agent Communication
- Message bus architecture using asyncio queues
- Shared memory through vector database
- Event-driven coordination via orchestrator

## 🔧 KEY FEATURES

### LLM Integration
- Support for Ollama (REST API) and llama.cpp (Python bindings)
- ReAct prompting with function calling
- Dynamic prompt assembly with context injection
- Support for models: Mixtral, LLaMA-3, OpenChat, CodeLlama

### Memory & Context
- ChromaDB for vector storage
- Local embeddings (sentence-transformers)
- Codebase indexing and semantic search
- Conversation history and task memory

### Execution Environment
- Docker-based sandboxing
- Secure command execution
- File system isolation
- Resource limits and monitoring

### Self-Healing
- Automatic error detection
- Code repair suggestions
- Test failure analysis
- Retry logic with learning

### Security & Privacy
- Fully offline operation
- No external API calls
- Sandboxed execution environment
- User permission controls