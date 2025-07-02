# 🧠 GodDevX - Autonomous Developer Assistant Platform

**Ultra-autonomous, offline-capable AI development assistant that works entirely with local LLMs**

GodDevX is a complete full-stack developer assistant platform that operates entirely offline using local LLMs like Mixtral, LLaMA-3, or OpenChat via Ollama or llama.cpp. It features multi-agent orchestration, self-healing capabilities, and comprehensive development tools.

## 🌟 Key Features

### 🧠 **Multi-Agent Architecture**
- **PlannerAgent**: Breaks down complex tasks into actionable steps
- **CoderAgent**: Generates, modifies, and refactors code
- **TerminalAgent**: Executes commands in sandboxed environment
- **DebuggerAgent**: Analyzes errors and implements fixes
- **GitAgent**: Manages version control operations
- **MemoryAgent**: Handles context and memory management
- **SearchAgent**: Searches and analyzes codebase

### 🔧 **Core Capabilities**
- **Fully Offline**: No external API calls, complete privacy
- **Local LLM Support**: Ollama, llama.cpp integration
- **ReAct Reasoning**: Advanced prompt engineering with function calling
- **Vector Memory**: ChromaDB + local embeddings for context
- **Sandboxed Execution**: Docker-based secure command execution
- **Self-Healing**: Automatic error detection and repair
- **Code Analysis**: Tree-sitter based AST parsing
- **Git Integration**: Full version control automation

### 🛡️ **Security & Privacy**
- **Offline Operation**: No data leaves your machine
- **Sandboxed Execution**: Isolated command execution environment
- **Permission Controls**: Fine-grained security policies
- **Resource Limits**: Memory and execution time constraints

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker (optional, for sandboxing)
- Ollama (for local LLM inference)

### Installation

1. **Install dependencies**
```bash
pip install -r requirements.txt
```

2. **Setup Ollama and download a model**
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Download a model (choose one)
ollama pull mixtral:8x7b      # Recommended for best performance
ollama pull llama3:8b         # Good balance of speed/quality
ollama pull openchat:7b       # Faster, good for development
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your preferences
```

4. **Run the system**
```bash
python main.py
```

### Docker Setup (Recommended)

```bash
# Start the complete stack
docker-compose up -d

# View logs
docker-compose logs -f goddevx
```

## 💬 Usage Examples

### Interactive Mode
```bash
python main.py
```

```
🧠 GodDevX> Create a Python web scraper for news articles with error handling

🤔 Processing...

✅ Result:
Created a robust web scraper with the following features:
- BeautifulSoup for HTML parsing
- Requests with retry logic and timeouts
- Comprehensive error handling for network issues
- Rate limiting to respect robots.txt
- Data validation and sanitization
- Logging for debugging
- Configuration file for easy customization

Files created:
- scraper.py (main scraper class)
- config.py (configuration settings)
- requirements.txt (dependencies)
- example_usage.py (usage examples)
```

## 🏗️ Architecture

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   LLM Engine    │    │  Agent System   │    │ Memory System   │
│                 │    │                 │    │                 │
│ • Ollama Client │    │ • Multi-Agent   │    │ • ChromaDB      │
│ • llama.cpp     │    │ • Orchestrator  │    │ • Embeddings    │
│ • ReAct Prompts │    │ • Message Bus   │    │ • Context RAG   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Execution Env   │    │  Tool System    │    │   UI Layer      │
│                 │    │                 │    │                 │
│ • Docker Sandbox│    │ • Code Parser   │    │ • FastAPI       │
│ • Terminal      │    │ • File Manager  │    │ • WebSocket     │
│ • Security      │    │ • Git Tools     │    │ • React UI      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

**GodDevX** - Empowering developers with autonomous AI assistance, completely offline and secure.
