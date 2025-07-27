from agentic_ai.core.llm.factory import LLMFactory
from langchain.llms.base import LLM
from langchain.callbacks.manager import CallbackManagerForLLMRun
from typing import Any, Dict, List, Optional, Union
import json
import re

class LangChainLLMWrapper(LLM):
    """Enhanced LangChain wrapper for custom LLM implementations with unified response formatting."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Use object.__setattr__ to bypass Pydantic validation
        object.__setattr__(self, '_llm', LLMFactory.get_llm())
    
    @property
    def _llm_type(self) -> str:
        return self._llm._llm_type

    def _enforce_react_format(self, response: str) -> str:
        """Apply uniform ReAct format enforcement for all LLM types.
        
        This ensures both Groq and OpenAI produce consistent outputs.
        """
        response = response.strip()
        
        # In case we got JSON or other non-standard output, try to extract text
        if response.startswith("{") and "}" in response:
            try:
                # Try to parse as JSON and extract relevant fields
                json_data = json.loads(response)
                # Look for common fields that might contain the actual thought
                for field in ["thought", "thinking", "reasoning", "response", "answer", "text", "content"]:
                    if field in json_data:
                        response = json_data[field]
                        print(f"Extracted response from JSON field: {field}")
                        break
            except:
                # If JSON parsing fails, continue with original response
                pass
        
        # CRITICAL: Reject responses with fake "Observation:" lines
        if "Observation:" in response:
            print("[DEBUG] Detected hallucinated Observation - replacing with simple action")
            # Extract just the thought and first action if any
            lines = response.split('\n')
            thought_line = None
            action_line = None
            action_input_line = None
            
            for line in lines:
                line = line.strip()
                if line.startswith("Thought:") and thought_line is None:
                    thought_line = line
                elif line.startswith("Action:") and action_line is None:
                    action_line = line
                elif line.startswith("Action Input:") and action_input_line is None:
                    action_input_line = line
                    break
            
            if thought_line and action_line and action_input_line:
                response = f"{thought_line}\n{action_line}\n{action_input_line}"
            else:
                response = "Thought: I need to ask for user input.\nAction: UserInteraction\nAction Input: Please provide more information."

        # Make sure response starts with "Thought:"
        if not response.startswith("Thought:"):
            response = f"Thought: {response}"
            
        # Check for missing Action: or Final Answer: after Thought:
        lines = response.split("\n")
        has_thought = False
        has_action_or_final = False
        
        for line in lines:
            line = line.strip()
            if line.startswith("Thought:"):
                has_thought = True
            if line.startswith("Action:") or line.startswith("Final Answer:"):
                has_action_or_final = True
                
        # If we have a Thought but no Action or Final Answer, append a default one
        if has_thought and not has_action_or_final:
            # Default to UserInteraction as safest option
            response += "\nAction: UserInteraction"
            response += "\nAction Input: Please provide more information for your loan application."
                    
        return response

    def _call(self, prompt: str, stop: Optional[List[str]] = None,
              run_manager: Optional[CallbackManagerForLLMRun] = None, **kwargs) -> str:
        """Call the underlying LLM with uniform format enforcement."""
        # Get the raw response from the LLM
        raw_response = self._llm._call(prompt, stop, **kwargs)
        
        # Apply consistent format enforcement for ALL LLM types
        # This ensures both Groq and OpenAI work identically
        if "Thought:" in prompt or "Action:" in prompt:
            formatted_response = self._enforce_react_format(raw_response)
        else:
            formatted_response = raw_response
            
        return formatted_response