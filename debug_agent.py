"""
A more comprehensive test script for debugging the agent initialization.
"""
import os
import sys
import traceback
from langchain.agents import Tool, AgentExecutor

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

def debug_agent_initialization():
    """Debug function with detailed error reporting."""
    try:
        # Import the factory
        from agentic_ai.core.orchestrator.agent_executor_factory import create_agent_executor
        
        print("✓ Successfully imported create_agent_executor")
        
        # Create a simple dummy tool
        dummy_tool = Tool(
            name="DummyTool",
            description="A dummy tool that does nothing",
            func=lambda x: f"Dummy result: {x}"
        )
        
        print("✓ Created dummy tool")
        
        # Try to create an agent executor with this tool
        print("Attempting to create agent executor...")
        agent_executor = create_agent_executor([dummy_tool])
        
        # Check if agent_executor was created
        if agent_executor and isinstance(agent_executor, AgentExecutor):
            print("✓ Success! Agent executor was created correctly.")
            print(f"Agent type: {type(agent_executor)}")
            
            # Test the agent with a simple input
            print("\nTesting agent with simple input...")
            try:
                result = agent_executor.invoke({"input": "Test request"})
                print("Agent returned result:", result)
                return True
            except Exception as e:
                print(f"❌ Error running agent: {str(e)}")
                print(traceback.format_exc())
                return False
        else:
            print("❌ Failed to create agent executor or wrong type returned.")
            print(f"Type returned: {type(agent_executor)}")
            return False
            
    except Exception as e:
        print(f"❌ Error in debug function: {str(e)}")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("AGENT INITIALIZATION DEBUGGING")
    print("=" * 50)
    success = debug_agent_initialization()
    print("\n" + "=" * 50)
    print(f"Final result: {'SUCCESS' if success else 'FAILURE'}")
    print("=" * 50)
