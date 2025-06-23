import logging
from langchain.callbacks.base import BaseCallbackHandler

def get_logger(name: str, level=logging.INFO):
    """
    Initializes and returns a logger.
    """
    logging.basicConfig(level=level,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    return logging.getLogger(name)

class DebugCallbackHandler(BaseCallbackHandler):
    """Custom callback for debugging AgentExecutor steps."""
    def on_agent_action(self, action, **kwargs):
        try:
            # Extract and display the thought preceding the action
            # This is the key part to restore the reasoning
            if hasattr(action, 'log') and isinstance(action.log, str):
                # Extract the thought from the log
                if "Thought:" in action.log:
                    thought_parts = action.log.split("Thought:", 1)
                    if len(thought_parts) > 1:
                        thought_text = thought_parts[1].split("Action:", 1)[0].strip()
                        # Make the thought output more prominent
                        print("\n" + "-" * 40)
                        print(f"💭 AGENT REASONING: {thought_text}")
                        print("-" * 40)
                else:
                    # If "Thought:" keyword isn't found, try to extract any reasoning before the Action
                    # Some agents may not follow the exact format
                    raw_log = action.log.strip()
                    if "Action:" in raw_log and len(raw_log.split("Action:", 1)[0]) > 5:
                        implicit_thought = raw_log.split("Action:", 1)[0].strip()
                        print("\n" + "-" * 40)
                        print(f"💭 IMPLICIT REASONING: {implicit_thought}")
                        print("-" * 40)
                    
            # Display the action in a user-friendly format
            print(f"🔄 Action: {action.tool}")
            print(f"📝 Action Input: {action.tool_input}")
        except Exception as e:
            print(f"[DEBUG] Error in agent action callback: {str(e)}")
            print(f"[DEBUG] Raw action: {action}")
            
            # Try to provide more helpful context for debugging
            if hasattr(action, 'log'):
                print(f"[DEBUG] Action log: {action.log}")

    def on_agent_observation(self, observation, **kwargs):
        try:
            # Truncate overly long observations to keep logs readable
            obs_str = str(observation)
            if len(obs_str) > 500:
                obs_str = obs_str[:500] + "... [truncated]"
            print(f"[DEBUG] Agent Observation: {obs_str}")
        except Exception as e:
            print(f"[DEBUG] Error in observation callback: {str(e)}")

    def on_agent_finish(self, finish, **kwargs):
        try:
            # Extract and display the final thought
            if hasattr(finish, 'log'):
                # First try standard format
                if "Thought:" in finish.log:
                    thought_parts = finish.log.split("Thought:", 1)
                    if len(thought_parts) > 1:
                        if "Final Answer:" in thought_parts[1]:
                            thought_text = thought_parts[1].split("Final Answer:", 1)[0].strip()
                        else:
                            # In case there's no Final Answer section
                            thought_text = thought_parts[1].strip()
                            
                        print("\n" + "=" * 50)
                        print(f"💭 FINAL REASONING:")
                        print(thought_text)
                        print("=" * 50)
                # Try to extract any reasoning before Final Answer if Thought isn't found
                elif "Final Answer:" in finish.log:
                    possible_thought = finish.log.split("Final Answer:", 1)[0].strip()
                    if len(possible_thought) > 10:  # Only if there's meaningful content
                        print("\n" + "=" * 50)
                        print(f"💭 FINAL REASONING:")
                        print(possible_thought)
                        print("=" * 50)
                    
            # Display the final answer in a user-friendly format
            if hasattr(finish, 'return_values') and 'output' in finish.return_values:
                print(f"\n✅ FINAL ANSWER: {finish.return_values['output']}\n")
        except Exception as e:
            print(f"[DEBUG] Error in finish callback: {str(e)}")
            
            # Try to print raw log for debugging
            if hasattr(finish, 'log'):
                print(f"Raw log: {finish.log}")
            
    def on_chain_error(self, error, **kwargs):
        print(f"[DEBUG] Chain error: {str(error)}")
        print(f"[DEBUG] This might be due to a response format issue between the LLM and the agent framework.")
        
    def on_chain_start(self, serialized, inputs, **kwargs):
        # Handle chain start events safely without accessing any attributes
        pass
        
    def on_chain_end(self, outputs, **kwargs):
        # Handle chain end events safely
        pass
        
    def on_llm_start(self, serialized, prompts, **kwargs):
        # Handle LLM start events safely
        pass
        
    def on_llm_end(self, response, **kwargs):
        # Handle LLM end events safely
        pass
        
    def on_llm_error(self, error, **kwargs):
        # Handle LLM error events safely
        pass
        
    def on_tool_start(self, serialized, input_str, **kwargs):
        # Handle tool start events safely
        pass
        
    def on_tool_end(self, output, **kwargs):
        # Handle tool end events safely
        pass
        
    def on_tool_error(self, error, **kwargs):
        # Handle tool error events safely
        pass
    
    def on_chain_end(self, outputs, **kwargs):
        # Handle chain end events safely
        pass
    
    def on_llm_start(self, serialized, prompts, **kwargs):
        # Handle LLM start events safely
        pass
    
    def on_llm_end(self, response, **kwargs):
        # Handle LLM end events safely
        pass
    
    def on_llm_error(self, error, **kwargs):
        # Handle LLM error events safely
        print(f"[DEBUG] LLM error: {str(error)}")
    
    def on_tool_start(self, serialized, input_str, **kwargs):
        # Handle tool start events safely
        pass
    
    def on_tool_end(self, output, **kwargs):
        # Handle tool end events safely
        pass
    
    def on_tool_error(self, error, **kwargs):
        # Handle tool error events safely
        print(f"[DEBUG] Tool error: {str(error)}")
