"""
Example: Feature Development Workflow

This example shows how GodDevX can implement new features from requirements.
"""

import asyncio
from main import GodDevXSystem


async def feature_development_example():
    """Example of automated feature development."""
    
    system = GodDevXSystem()
    
    if not await system.initialize():
        print("Failed to initialize system")
        return
    
    # Example feature request
    feature_request = """
    I need to add OAuth2 authentication to my Flask web application.
    
    Requirements:
    - Support Google and GitHub OAuth providers
    - Store user sessions securely
    - Protect certain routes that require authentication
    - Add login/logout functionality
    - Handle OAuth callback and error cases
    
    The current app structure:
    - app.py (main Flask app)
    - models.py (database models)
    - templates/ (HTML templates)
    - static/ (CSS/JS files)
    
    Please implement this feature with proper error handling and security.
    """
    
    print("🚀 Processing feature request...")
    result = await system.process_task(feature_request)
    print(f"\n✅ Feature implementation result:\n{result}")
    
    await system.shutdown()


if __name__ == "__main__":
    asyncio.run(feature_development_example())