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
            # Try to infer what tool the model was trying to use
            lower_resp = response.lower()
            tool_map = {
                "dataquery": "DataQuery",
                "userinteraction": "UserInteraction", 
                "user interaction": "UserInteraction",
                "geopolicycheck": "GeoPolicyCheck",
                "geo policy": "GeoPolicyCheck",
                "riskassessment": "RiskAssessment", 
                "risk assessment": "RiskAssessment",
                "salarysheetgenerator": "SalarySheetGenerator",
                "salarysheetretriever": "SalarySheetRetriever"
            }
            
            selected_tool = None
            for keyword, tool_name in tool_map.items():
                if keyword in lower_resp:
                    selected_tool = tool_name
                    break
                    
            if not selected_tool:
                # Check if it seems like a final answer
                final_indicators = ["loan", "approved", "rejected", "interest", "rate", "application"]
                final_answer_likely = any(indicator in lower_resp for indicator in final_indicators)
                
                if final_answer_likely:
                    response += "\nFinal Answer: " + response.split("Thought:")[1].strip()
                else:
                    # Default to UserInteraction as safest option
                    response += "\nAction: UserInteraction"
                    response += "\nAction Input: Please provide more information for your loan application."
            else:
                response += f"\nAction: {selected_tool}"
                
                # Try to extract appropriate input based on content
                if selected_tool == "UserInteraction":
                    # Look for question marks in the text
                    question_match = re.search(r"[^.?!]*\?", lower_resp)
                    if question_match:
                        response += f"\nAction Input: {question_match.group(0).strip()}"
                    else:
                        response += "\nAction Input: Please provide more information for your loan application."
                elif selected_tool == "DataQuery":
                    # Look for PAN or Aadhaar-like patterns
                    id_match = re.search(r"[A-Z0-9]{10,12}", response)
                    if id_match:
                        response += f"\nAction Input: {id_match.group(0)}"
                    else:
                        response += "\nAction Input: [PAN/Aadhaar provided by user]"
                else:
                    response += f"\nAction Input: [Input for {selected_tool}]"
                    
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