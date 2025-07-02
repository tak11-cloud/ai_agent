"""
Example: Automated Bug Fixing Workflow

This example demonstrates how GodDevX can automatically analyze and fix bugs.
"""

import asyncio
from main import GodDevXSystem


async def bug_fix_example():
    """Example of automated bug fixing."""
    
    system = GodDevXSystem()
    
    if not await system.initialize():
        print("Failed to initialize system")
        return
    
    # Example bug report
    bug_report = """
    I'm getting a TypeError in my Python web scraper:
    
    File "scraper.py", line 45, in parse_article
        title = soup.find('h1').text.strip()
    TypeError: 'NoneType' object has no attribute 'text'
    
    The scraper works for some websites but fails on others.
    Can you help me fix this and make it more robust?
    """
    
    print("🐛 Processing bug report...")
    result = await system.process_task(bug_report)
    print(f"\n✅ Bug fix result:\n{result}")
    
    await system.shutdown()


if __name__ == "__main__":
    asyncio.run(bug_fix_example())