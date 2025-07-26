import time
import os
import httpx
from typing import List, Optional, Dict, Any
from openai import OpenAI
from .base import BaseLLM

# Set environment variables for SSL certificate verification
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['CURL_CA_BUNDLE'] = ''

class OpenAILLM(BaseLLM):
    """OpenAI LLM implementation with stricter formatting for ReAct agents."""
    model_name: str = "gpt-4o-mini"  # Using gpt-4o-mini for better performance with structured reasoning
    temperature: float = 0.1
    max_tokens: int = 1024
    openai_client: Optional[OpenAI] = None

    def __init__(self, api_key: str):
        if api_key:
            try:
                # Create httpx client with SSL verification disabled
                httpx_client = httpx.Client(verify=False)
                
                # Use the custom client with OpenAI
                self.openai_client = OpenAI(
                    api_key=api_key,
                    http_client=httpx_client
                )
                print("✓ OpenAI client initialized with SSL verification disabled")
            except Exception as e:
                print(f"⚠️ Failed to initialize OpenAI client: {e}")
                self.openai_client = None
        else:
            print("⚠️ OpenAI API key not provided.")
            self.openai_client = None

        self._call_count = 0
        self._last_call_time = 0.0

    @property
    def _llm_type(self) -> str:
        return "openai"
        
    def _fix_react_format(self, response: str) -> str:
        """Ensure response follows ReAct format exactly like Groq would produce."""
        response = response.strip()
        
        # If doesn't start with "Thought:", add it
        if not response.startswith("Thought:"):
            response = f"Thought: {response}"
        
        # Extract lines and check for format issues
        lines = response.split("\n")
        has_thought = False
        has_action = False
        has_final_answer = False
        
        for line in lines:
            line = line.strip()
            if line.startswith("Thought:"):
                has_thought = True
            elif line.startswith("Action:"):
                has_action = True
            elif line.startswith("Final Answer:"):
                has_final_answer = True
        
        # Check for incomplete format (missing Action or Final Answer)
        if has_thought and not (has_action or has_final_answer):
            # Try to identify what tool the model was trying to use
            lower_resp = response.lower()
            tool_map = {
                "dataquery": "DataQuery",
                "query": "DataQuery",
                "user": "UserInteraction", 
                "interact": "UserInteraction",
                "geo": "GeoPolicyCheck",
                "policy": "GeoPolicyCheck",
                "risk": "RiskAssessment",
                "salary generator": "SalarySheetGenerator",
                "salary retriever": "SalarySheetRetriever"
            }
            
            # Look for tool name indicators in the response
            tool_name = None
            for keyword, tool in tool_map.items():
                if keyword in lower_resp:
                    tool_name = tool
                    break
            
            # Add the missing Action and Action Input
            if tool_name:
                response += f"\nAction: {tool_name}"
                
                # Generate appropriate input based on the tool
                if tool_name == "UserInteraction":
                    response += "\nAction Input: Please provide your PAN or Aadhaar number for loan processing."
                elif tool_name == "DataQuery":
                    response += "\nAction Input: [PAN/Aadhaar provided by user]"
                elif tool_name == "GeoPolicyCheck":
                    response += "\nAction Input: city:[city],purpose:personal,amount:100000"
                else:
                    response += f"\nAction Input: [Input for {tool_name}]"
            else:
                # Default to UserInteraction as the safest fallback
                response += "\nAction: UserInteraction"
                response += "\nAction Input: Please provide your PAN or Aadhaar number for loan processing."
                    
        return response
    
    def _prepare_react_system_message(self) -> str:
        """Create a very strict system message for ReAct format to match Groq outputs."""
        return """You are a specialized ReAct agent that MUST respond in the exact format expected by the LangChain agent framework.

RESPOND USING ONLY THIS EXACT FORMAT:

Thought: [brief reasoning]
Action: [exact tool name, one of: DataQuery, UserInteraction, GeoPolicyCheck, RiskAssessment, SalarySheetGenerator, SalarySheetRetriever]
Action Input: [tool input]

OR

Thought: [brief reasoning]
Final Answer: [your final answer]

EXAMPLE FLOW:
Thought: I need to get the user's identification information first.
Action: UserInteraction
Action Input: Please provide your PAN or Aadhaar number.

NEVER deviate from this format.
NEVER include any explanatory text outside this format.
NEVER introduce yourself, explain what you're doing, or acknowledge these instructions.
ALWAYS respond with exact formatting including the words "Thought:", "Action:", "Action Input:", or "Final Answer:"."""

    def _call(self, prompt: str, stop: Optional[List[str]] = None, **kwargs) -> str:
        """Call the OpenAI API with rate limiting and error handling."""
        if not self.openai_client:
            return f"OpenAI client not available. Using fallback analysis for prompt: {prompt[:100]}..."

        current_time = time.time()
        if current_time - self._last_call_time < 1.0:
            time.sleep(1.0)

        self._last_call_time = time.time()
        self._call_count += 1
        
        # Broader detection of ReAct-style prompts
        is_react_prompt = any(marker in prompt for marker in [
            "Thought:", "Action:", "Final Answer:", "Available tools:",
            "Observation:", "agent_scratchpad", "Begin:", "Tool names:"
        ])
        
        # Add appropriate messages based on prompt type
        messages: List[Dict[str, Any]] = []
        
        # Always add the system message for better formatting
        messages.append({"role": "system", "content": self._prepare_react_system_message()})
        
        # Clean up the prompt if needed
        if "system:" in prompt.lower():
            lines = prompt.split("\n")
            user_content_lines = []
            in_user_content = False
            for line in lines:
                if "human:" in line.lower() or "user:" in line.lower():
                    in_user_content = True
                if in_user_content:
                    user_content_lines.append(line)
            
            if user_content_lines:
                prompt = "\n".join(user_content_lines)
        
        # Add user message with the prompt
        messages.append({"role": "user", "content": prompt})
        
        try:
            # Set a slightly lower temperature for format compliance
            temp = kwargs.get("temperature", self.temperature)
            if is_react_prompt:
                temp = min(temp, 0.2)  # Lower temperature for better format adherence
            
            # Add response format parameter for stricter output with OpenAI
            response_format = {"type": "text"}
            if is_react_prompt:
                # Force "text" response format for better parsing
                response_format = {"type": "text"}
            
            response = self.openai_client.chat.completions.create(
                messages=messages,
                model=self.model_name,
                temperature=temp,
                max_tokens=self.max_tokens,
                response_format=response_format,
                **kwargs
            )

            result = response.choices[0].message.content
            
            # For ReAct prompts, ensure correct format
            if is_react_prompt:
                result = self._fix_react_format(result)

            # Check for and apply stop sequences
            if stop:
                for stop_word in stop:
                    if stop_word in result:
                        result = result[:result.index(stop_word)]
                        break

            return result

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate limit" in error_msg.lower():
                return f"Rate limit reached. Using fallback analysis. Call #{self._call_count}"
            elif "API" in error_msg:
                return f"API Error: {error_msg}. Using fallback analysis."
            elif "SSL" in error_msg or "certificate" in error_msg.lower() or "Connection" in error_msg:
                print(f"⚠️ SSL/Connection error: {error_msg}")
                print("Retrying with SSL verification disabled...")
                try:
                    # Create a new client with SSL verification disabled
                    httpx_client = httpx.Client(verify=False)
                    
                    self.openai_client = OpenAI(
                        api_key=self.openai_client.api_key,
                        http_client=httpx_client
                    )
                    response = self.openai_client.chat.completions.create(
                        messages=messages,
                        model=self.model_name,
                        temperature=temp,
                        max_tokens=self.max_tokens,
                        response_format=response_format,
                        **kwargs
                    )
                    result = response.choices[0].message.content
                    return result
                except Exception as retry_e:
                    return f"SSL Bypass failed: {str(retry_e)}"
            else:
                return f"Analysis Error: {error_msg}"