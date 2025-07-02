#!/usr/bin/env python3
"""
GodDevX Demo - Demonstrates the system without requiring Ollama.
"""

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from memory import VectorMemory, LocalEmbeddings
from tools import FileManager
from executor import TerminalRunner


class DemoSystem:
    """Demo version of GodDevX system."""
    
    def __init__(self):
        self.file_manager = None
        self.memory = None
        self.terminal = None
    
    async def initialize(self):
        """Initialize demo system."""
        
        print("🧠 Initializing GodDevX Demo System...")
        
        # Create demo workspace
        os.makedirs("./demo_workspace", exist_ok=True)
        os.makedirs("./demo_data/memory", exist_ok=True)
        
        # Initialize components
        self.file_manager = FileManager("./demo_workspace")
        self.terminal = TerminalRunner(working_directory="./demo_workspace")
        
        # Initialize memory (with graceful fallback)
        try:
            embeddings = LocalEmbeddings()
            self.memory = VectorMemory(
                collection_name="demo_memory",
                persist_directory="./demo_data/memory"
            )
            print("✅ Memory system initialized")
        except Exception as e:
            print(f"⚠️  Memory system unavailable: {e}")
            self.memory = None
        
        print("✅ Demo system initialized successfully!")
        return True
    
    async def demo_file_operations(self):
        """Demonstrate file operations."""
        
        print("\n📁 Demonstrating File Operations...")
        
        # Create a sample Python file
        sample_code = '''"""
Sample Python module for demonstration.
"""

def greet(name: str) -> str:
    """Greet a person by name."""
    return f"Hello, {name}!"

def calculate_fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

class Calculator:
    """Simple calculator class."""
    
    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        return a + b
    
    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        return a * b

if __name__ == "__main__":
    print(greet("GodDevX"))
    print(f"Fibonacci(10) = {calculate_fibonacci(10)}")
    
    calc = Calculator()
    print(f"5 + 3 = {calc.add(5, 3)}")
    print(f"4 * 7 = {calc.multiply(4, 7)}")
'''
        
        # Write the file
        await self.file_manager.write_file("sample.py", sample_code)
        print("✅ Created sample.py")
        
        # Read and display file info
        content = await self.file_manager.read_file("sample.py")
        print(f"✅ File size: {len(content)} characters")
        
        # List files
        files = await self.file_manager.list_files()
        print(f"✅ Files in workspace: {len(files)} files")
        
        # Create a configuration file
        config_content = '''# GodDevX Demo Configuration
app_name = "GodDevX Demo"
version = "1.0.0"
debug = true

[database]
host = "localhost"
port = 5432
name = "goddevx_demo"

[llm]
provider = "ollama"
model = "mixtral:8x7b"
temperature = 0.3
'''
        
        await self.file_manager.write_file("config.toml", config_content)
        print("✅ Created config.toml")
        
        return True
    
    async def demo_terminal_operations(self):
        """Demonstrate terminal operations."""
        
        print("\n🔧 Demonstrating Terminal Operations...")
        
        # List directory contents
        result = await self.terminal.execute_command("ls -la")
        print(f"✅ Directory listing:")
        print(f"   Exit code: {result.exit_code}")
        print(f"   Output: {result.stdout[:200]}...")
        
        # Check Python syntax
        result = await self.terminal.execute_command("python -m py_compile sample.py")
        if result.exit_code == 0:
            print("✅ Python syntax check passed")
        else:
            print(f"❌ Python syntax check failed: {result.stderr}")
        
        # Run the sample script
        result = await self.terminal.execute_command("python sample.py")
        print(f"✅ Script execution:")
        print(f"   Exit code: {result.exit_code}")
        print(f"   Output:\n{result.stdout}")
        
        return True
    
    async def demo_memory_operations(self):
        """Demonstrate memory operations."""
        
        print("\n💾 Demonstrating Memory Operations...")
        
        if not self.memory:
            print("⚠️  Memory system not available, skipping demo")
            return True
        
        # Store some information
        sample_docs = [
            ("Python is a high-level programming language known for its simplicity and readability.", {"type": "language_info"}),
            ("FastAPI is a modern web framework for building APIs with Python.", {"type": "framework_info"}),
            ("ChromaDB is a vector database designed for AI applications.", {"type": "database_info"}),
            ("Docker provides containerization for consistent deployment environments.", {"type": "tool_info"}),
            ("Git is a distributed version control system for tracking code changes.", {"type": "tool_info"})
        ]
        
        stored_ids = []
        for doc, metadata in sample_docs:
            doc_id = await self.memory.store_text(doc, metadata)
            stored_ids.append(doc_id)
        
        print(f"✅ Stored {len(stored_ids)} documents in memory")
        
        # Search for information
        search_queries = [
            "Python programming language",
            "web framework API",
            "version control"
        ]
        
        for query in search_queries:
            results = await self.memory.search(query, limit=2)
            print(f"✅ Search '{query}': {len(results)} results")
            for result in results:
                print(f"   - {result.text[:60]}... (score: {result.score:.2f})")
        
        return True
    
    async def demo_code_analysis(self):
        """Demonstrate code analysis capabilities."""
        
        print("\n🔍 Demonstrating Code Analysis...")
        
        # Read the sample file
        content = await self.file_manager.read_file("sample.py")
        
        # Simple code analysis
        lines = content.split('\n')
        
        # Count different elements
        functions = [line for line in lines if line.strip().startswith('def ')]
        classes = [line for line in lines if line.strip().startswith('class ')]
        imports = [line for line in lines if line.strip().startswith('import ') or line.strip().startswith('from ')]
        comments = [line for line in lines if line.strip().startswith('#')]
        docstrings = [line for line in lines if '"""' in line]
        
        print(f"✅ Code analysis results:")
        print(f"   - Total lines: {len(lines)}")
        print(f"   - Functions: {len(functions)}")
        print(f"   - Classes: {len(classes)}")
        print(f"   - Imports: {len(imports)}")
        print(f"   - Comments: {len(comments)}")
        print(f"   - Docstrings: {len(docstrings) // 2}")  # Assuming paired docstrings
        
        # Show function signatures
        print(f"✅ Function definitions found:")
        for func in functions:
            print(f"   - {func.strip()}")
        
        return True
    
    async def demo_workflow(self):
        """Demonstrate a complete workflow."""
        
        print("\n🔄 Demonstrating Complete Workflow...")
        
        # Simulate a bug fix workflow
        print("📋 Scenario: Fix a bug in the Fibonacci function")
        
        # 1. Analyze the problem
        print("1️⃣ Analyzing the current implementation...")
        content = await self.file_manager.read_file("sample.py")
        
        # 2. Identify the issue (inefficient recursive implementation)
        print("2️⃣ Issue identified: Inefficient recursive Fibonacci implementation")
        
        # 3. Create an improved version
        improved_code = content.replace(
            '''def calculate_fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)''',
            '''def calculate_fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number using dynamic programming."""
    if n <= 1:
        return n
    
    # Use dynamic programming for efficiency
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b'''
        )
        
        # 4. Write the improved version
        await self.file_manager.write_file("sample_improved.py", improved_code)
        print("3️⃣ Created improved version: sample_improved.py")
        
        # 5. Test the improved version
        result = await self.terminal.execute_command("python sample_improved.py")
        print("4️⃣ Testing improved version:")
        print(f"   Exit code: {result.exit_code}")
        print(f"   Output:\n{result.stdout}")
        
        # 6. Store the improvement in memory
        if self.memory:
            await self.memory.store_text(
                "Improved Fibonacci function using dynamic programming instead of recursion for better performance.",
                {"type": "improvement", "file": "sample.py", "function": "calculate_fibonacci"}
            )
            print("5️⃣ Stored improvement details in memory")
        
        print("✅ Workflow completed successfully!")
        return True
    
    async def run_demo(self):
        """Run the complete demo."""
        
        print("""
🧠 GodDevX - Autonomous Developer Assistant Platform
====================================================
DEMO MODE - Showcasing core capabilities without LLM
""")
        
        # Initialize system
        if not await self.initialize():
            print("❌ Failed to initialize demo system")
            return False
        
        # Run demonstrations
        demos = [
            ("File Operations", self.demo_file_operations),
            ("Terminal Operations", self.demo_terminal_operations),
            ("Memory Operations", self.demo_memory_operations),
            ("Code Analysis", self.demo_code_analysis),
            ("Complete Workflow", self.demo_workflow)
        ]
        
        for demo_name, demo_func in demos:
            try:
                print(f"\n{'='*60}")
                await demo_func()
                print(f"✅ {demo_name} demo completed")
            except Exception as e:
                print(f"❌ {demo_name} demo failed: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n{'='*60}")
        print("🎉 GodDevX Demo completed!")
        print("\nKey capabilities demonstrated:")
        print("  ✅ File management and code manipulation")
        print("  ✅ Terminal command execution")
        print("  ✅ Vector memory storage and retrieval")
        print("  ✅ Code analysis and pattern recognition")
        print("  ✅ Automated workflow execution")
        print("\nTo use with a real LLM:")
        print("  1. Install and start Ollama")
        print("  2. Download a model: ollama pull mixtral:8x7b")
        print("  3. Run: python main.py")
        
        return True


async def main():
    """Main demo function."""
    
    demo = DemoSystem()
    success = await demo.run_demo()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)