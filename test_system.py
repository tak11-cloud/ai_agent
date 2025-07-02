#!/usr/bin/env python3
"""
Simple test to verify the GodDevX system works.
"""

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_basic_functionality():
    """Test basic system functionality."""
    
    print("🧠 Testing GodDevX System Components...")
    
    try:
        # Test configuration
        print("📋 Testing configuration...")
        from config.settings import settings
        print(f"✅ Settings loaded: {settings.app_name}")
        
        # Test LLM engine
        print("🤖 Testing LLM engine...")
        from llm_engine import OllamaClient, LLMConfig
        
        llm_config = LLMConfig(model_name="test-model")
        llm_client = OllamaClient(llm_config)
        print("✅ LLM client created")
        
        # Test memory system
        print("💾 Testing memory system...")
        from memory import VectorMemory, LocalEmbeddings
        
        embeddings = LocalEmbeddings()
        memory = VectorMemory(
            collection_name="test_memory",
            persist_directory="./test_data/memory"
        )
        print("✅ Memory system created")
        
        # Test executor
        print("🔧 Testing executor...")
        from executor import TerminalRunner
        
        terminal = TerminalRunner(working_directory="./test_workspace")
        print("✅ Terminal runner created")
        
        # Test tools
        print("🛠️ Testing tools...")
        from tools import FileManager
        
        file_manager = FileManager("./test_workspace")
        print("✅ File manager created")
        
        print("\n🎉 All basic components working!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_simple_workflow():
    """Test a simple workflow without LLM."""
    
    print("\n🔄 Testing simple workflow...")
    
    try:
        from tools import FileManager
        
        # Create file manager
        file_manager = FileManager("./test_workspace")
        
        # Create a test file
        await file_manager.write_file("test.txt", "Hello, GodDevX!")
        print("✅ Created test file")
        
        # Read the file
        content = await file_manager.read_file("test.txt")
        print(f"✅ Read file content: {content}")
        
        # List files
        files = await file_manager.list_files()
        print(f"✅ Listed files: {len(files)} files found")
        
        print("🎉 Simple workflow completed!")
        return True
        
    except Exception as e:
        print(f"❌ Workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function."""
    
    print("""
🧠 GodDevX - Autonomous Developer Assistant Platform
====================================================
Running system tests...
""")
    
    # Create test directories
    os.makedirs("./test_data/memory", exist_ok=True)
    os.makedirs("./test_workspace", exist_ok=True)
    
    # Run tests
    basic_test = await test_basic_functionality()
    workflow_test = await test_simple_workflow()
    
    if basic_test and workflow_test:
        print("\n✅ All tests passed! GodDevX system is ready.")
        print("\nTo start the system:")
        print("  python main.py")
        return 0
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)