import time
import os
import requests
from typing import Dict, List, Optional, Any
from .base import BaseLLM

class OllamaLLM(BaseLLM):
    """Ollama LLM implementation for local LLM inference."""

    model_name: str = "llama3"  # Default model
    temperature: float = 0.1
    max_tokens: int = 1024
    base_url: str = "http://localhost:11434"  # Default Ollama API endpoint

    def __init__(self, base_url: Optional[str] = None):
        """Initialize the Ollama LLM client.
        
        Args:
            base_url: Optional custom Ollama API endpoint URL.
        """
        self.base_url = base_url or os.getenv("OLLAMA_API_URL", self.base_url)
        self._call_count = 0
        self._last_call_time = 0.0
        
        # Verify if Ollama is accessible
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                print(f"✓ Connected to Ollama server at {self.base_url}")
            else:
                print(f"⚠️ Ollama server responded with status code: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Failed to connect to Ollama server at {self.base_url}: {e}")

    @property
    def _llm_type(self) -> str:
        return "ollama"

    def _call(self, prompt: str, stop: Optional[List[str]] = None, **kwargs) -> str:
        """Call the Ollama API with error handling."""
        current_time = time.time()
        if current_time - self._last_call_time < 0.5:  # Local LLMs can handle more requests
            time.sleep(0.5)

        self._last_call_time = time.time()
        self._call_count += 1
        
        # Prepare the request payload
        payload: Dict[str, Any] = {
            "model": kwargs.get("model", self.model_name),
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", self.temperature),
                "num_predict": kwargs.get("max_tokens", self.max_tokens),
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate", 
                json=payload
            )
            
            if response.status_code != 200:
                return f"Ollama API error: {response.status_code} - {response.text[:100]}"
                
            result = response.json().get("response", "")
            
            # Handle stop sequences if provided
            if stop:
                for stop_word in stop:
                    if stop_word in result:
                        result = result[:result.index(stop_word)]
                        break
                        
            return result
            
        except Exception as e:
            return f"Ollama Analysis Error: {str(e)}"
