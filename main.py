"""
GodDevX - Autonomous Developer Assistant Platform

Main entry point for the agent runtime system.
"""

import asyncio
import signal
import sys
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from config.settings import settings
from llm_engine import OllamaClient, LLMConfig
from memory import VectorMemory, LocalEmbeddings
from agents import (
    PlannerAgent, CoderAgent, TerminalAgent, DebuggerAgent,
    GitAgent, AgentOrchestrator
)
from agents.git_agent import MemoryAgent, SearchAgent
from executor import TerminalRunner
from tools import FileManager


class GodDevXSystem:
    """Main system orchestrator for the autonomous developer assistant."""
    
    def __init__(self):
        self.settings = settings
        self.running = False
        self.agents: Dict[str, Any] = {}
        self.orchestrator: Optional[AgentOrchestrator] = None
        
        # Core components
        self.llm_client = None
        self.memory = None
        self.terminal_runner = None
        self.file_manager = None
        
        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
    
    def _setup_logging(self):
        """Setup logging configuration."""
        
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(log_format))
        
        # File handler
        if self.settings.log_file:
            file_handler = logging.FileHandler(self.settings.log_file)
            file_handler.setLevel(logging.DEBUG if self.settings.debug else logging.INFO)
            file_handler.setFormatter(logging.Formatter(log_format))
        
        # Root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG if self.settings.debug else logging.INFO)
        root_logger.addHandler(console_handler)
        
        if self.settings.log_file:
            root_logger.addHandler(file_handler)
    
    async def initialize(self) -> bool:
        """Initialize all system components."""
        
        self.logger.info("🧠 Initializing GodDevX System...")
        
        try:
            # Validate settings
            errors = self.settings.validate_settings()
            if errors:
                self.logger.error("Configuration errors:")
                for error in errors:
                    self.logger.error(f"  - {error}")
                return False
            
            # Initialize LLM client
            self.logger.info("🤖 Initializing LLM client...")
            llm_config = LLMConfig(**self.settings.get_llm_config_dict())
            
            if self.settings.llm.provider == "ollama":
                self.llm_client = OllamaClient(llm_config, self.settings.llm.base_url)
            else:
                self.logger.error(f"Unsupported LLM provider: {self.settings.llm.provider}")
                return False
            
            # Connect to LLM
            if not await self.llm_client.connect():
                self.logger.error("Failed to connect to LLM service")
                return False
            
            self.logger.info(f"✅ Connected to {self.settings.llm.provider} with model {self.settings.llm.model_name}")
            
            # Initialize memory system
            self.logger.info("💾 Initializing memory system...")
            embeddings = LocalEmbeddings(self.settings.memory.embedding_model_name)
            self.memory = VectorMemory(
                collection_name=self.settings.memory.collection_name,
                persist_directory=self.settings.memory.persist_directory,
                embedding_model=embeddings
            )
            
            # Initialize executor
            self.logger.info("🔧 Initializing execution environment...")
            self.terminal_runner = TerminalRunner(
                working_directory=self.settings.executor.working_directory,
                default_timeout=self.settings.executor.max_execution_time,
                use_sandbox=self.settings.executor.use_sandbox
            )
            
            # Test terminal execution
            if not await self.terminal_runner.test_command_execution():
                self.logger.warning("Terminal execution test failed")
            
            # Initialize file manager
            self.logger.info("📁 Initializing file manager...")
            self.file_manager = FileManager(self.settings.executor.working_directory)
            
            # Initialize agents
            await self._initialize_agents()
            
            # Initialize orchestrator
            self.logger.info("🎭 Initializing agent orchestrator...")
            self.orchestrator = AgentOrchestrator(
                agents=self.agents,
                memory=self.memory
            )
            
            self.logger.info("✅ GodDevX System initialized successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize system: {e}")
            return False
    
    async def _initialize_agents(self):
        """Initialize all agents."""
        
        self.logger.info("🧠 Initializing agents...")
        
        enabled_agents = self.settings.get_enabled_agents()
        
        for agent_name in enabled_agents:
            try:
                agent_config = self.settings.get_agent_config(agent_name)
                
                if agent_name == "planner":
                    agent = PlannerAgent(
                        name="PlannerAgent",
                        llm=self.llm_client,
                        memory=self.memory,
                        max_iterations=agent_config.max_iterations
                    )
                elif agent_name == "coder":
                    agent = CoderAgent(
                        name="CoderAgent",
                        llm=self.llm_client,
                        memory=self.memory,
                        max_iterations=agent_config.max_iterations
                    )
                elif agent_name == "terminal":
                    agent = TerminalAgent(
                        name="TerminalAgent",
                        llm=self.llm_client,
                        memory=self.memory,
                        terminal_runner=self.terminal_runner,
                        max_iterations=agent_config.max_iterations
                    )
                elif agent_name == "debugger":
                    agent = DebuggerAgent(
                        name="DebuggerAgent",
                        llm=self.llm_client,
                        memory=self.memory,
                        max_iterations=agent_config.max_iterations
                    )
                elif agent_name == "git":
                    agent = GitAgent(
                        name="GitAgent",
                        llm=self.llm_client,
                        memory=self.memory,
                        max_iterations=agent_config.max_iterations
                    )
                elif agent_name == "memory":
                    agent = MemoryAgent(
                        name="MemoryAgent",
                        llm=self.llm_client,
                        memory=self.memory,
                        max_iterations=agent_config.max_iterations
                    )
                elif agent_name == "search":
                    agent = SearchAgent(
                        name="SearchAgent",
                        llm=self.llm_client,
                        memory=self.memory,
                        file_manager=self.file_manager,
                        max_iterations=agent_config.max_iterations
                    )
                else:
                    self.logger.warning(f"Unknown agent type: {agent_name}")
                    continue
                
                self.agents[agent_name] = agent
                self.logger.info(f"✅ Initialized {agent_name} agent")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize {agent_name} agent: {e}")
    
    async def process_task(self, task: str, context: Dict[str, Any] = None) -> str:
        """Process a user task through the agent system."""
        
        if not self.orchestrator:
            return "System not initialized"
        
        self.logger.info(f"📝 Processing task: {task}")
        
        try:
            # Store task in memory
            await self.memory.store_text(
                text=f"User task: {task}",
                metadata={
                    "type": "user_task",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Process through orchestrator
            result = await self.orchestrator.process_task(task, context or {})
            
            # Store result in memory
            await self.memory.store_text(
                text=f"Task result: {result}",
                metadata={
                    "type": "task_result",
                    "timestamp": datetime.now().isoformat(),
                    "original_task": task
                }
            )
            
            self.logger.info("✅ Task completed successfully")
            return result
            
        except Exception as e:
            error_msg = f"Error processing task: {str(e)}"
            self.logger.error(error_msg)
            return error_msg
    
    async def start_interactive_mode(self):
        """Start interactive command-line mode."""
        
        self.logger.info("🎮 Starting interactive mode...")
        self.logger.info("Type 'help' for commands, 'exit' to quit")
        
        while self.running:
            try:
                # Get user input
                user_input = input("\n🧠 GodDevX> ").strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.lower() in ['exit', 'quit', 'q']:
                    break
                elif user_input.lower() == 'help':
                    self._show_help()
                    continue
                elif user_input.lower() == 'status':
                    await self._show_status()
                    continue
                elif user_input.lower() == 'agents':
                    self._show_agents()
                    continue
                elif user_input.lower().startswith('clear'):
                    self.memory.clear_collection()
                    print("Memory cleared")
                    continue
                
                # Process as task
                print("\n🤔 Processing...")
                result = await self.process_task(user_input)
                print(f"\n✅ Result:\n{result}")
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except EOFError:
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
    
    def _show_help(self):
        """Show help information."""
        
        help_text = """
🧠 GodDevX - Autonomous Developer Assistant

Available Commands:
  help     - Show this help message
  status   - Show system status
  agents   - Show agent information
  clear    - Clear memory
  exit     - Exit the system

Task Examples:
  "Create a Python web scraper for news articles"
  "Add OAuth2 authentication to my Flask app"
  "Fix the bug in the user registration function"
  "Write unit tests for the payment module"
  "Refactor the database connection code"
  "Set up CI/CD pipeline with GitHub Actions"
"""
        print(help_text)
    
    async def _show_status(self):
        """Show system status."""
        
        print("\n📊 System Status:")
        print(f"  LLM: {self.settings.llm.provider} ({self.settings.llm.model_name})")
        print(f"  Memory: {await self._get_memory_stats()}")
        print(f"  Agents: {len(self.agents)} active")
        print(f"  Working Directory: {self.settings.executor.working_directory}")
        
        # Test LLM connection
        if self.llm_client:
            health = await self.llm_client.health_check()
            print(f"  LLM Health: {'✅ OK' if health else '❌ Failed'}")
    
    def _show_agents(self):
        """Show agent information."""
        
        print("\n🤖 Active Agents:")
        for name, agent in self.agents.items():
            status = agent.get_status()
            print(f"  {name}: {status['state']} - {len(status.get('capabilities', []))} capabilities")
    
    async def _get_memory_stats(self) -> str:
        """Get memory statistics."""
        
        try:
            stats = await self.memory.get_stats()
            return f"{stats['total_documents']} documents"
        except Exception:
            return "Unknown"
    
    async def shutdown(self):
        """Shutdown the system gracefully."""
        
        self.logger.info("🛑 Shutting down GodDevX System...")
        self.running = False
        
        # Stop all agents
        for agent in self.agents.values():
            await agent.reset()
        
        # Kill running processes
        if self.terminal_runner:
            killed = await self.terminal_runner.kill_all_processes()
            if killed > 0:
                self.logger.info(f"Killed {killed} running processes")
        
        # Disconnect LLM
        if self.llm_client:
            await self.llm_client.disconnect()
        
        self.logger.info("✅ System shutdown complete")
    
    async def run(self):
        """Main run loop."""
        
        # Initialize system
        if not await self.initialize():
            self.logger.error("Failed to initialize system")
            return 1
        
        self.running = True
        
        # Setup signal handlers
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Start interactive mode
            await self.start_interactive_mode()
            
        except Exception as e:
            self.logger.error(f"Runtime error: {e}")
            return 1
        
        finally:
            await self.shutdown()
        
        return 0


async def main():
    """Main entry point."""
    
    print("""
🧠 GodDevX - Autonomous Developer Assistant Platform
====================================================
Ultra-autonomous, offline-capable AI development assistant
""")
    
    system = GodDevXSystem()
    return await system.run()


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)