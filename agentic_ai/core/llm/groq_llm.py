import time
from typing import Any, List, Optional
from groq import Groq
from .base import BaseLLM

class GroqLLM(BaseLLM):
    """Groq LLM implementation."""

    model_name: str = "llama-3.3-70b-versatile"
    temperature: float = 0.1
    max_tokens: int = 1024
    groq_client: Any = None

    def __init__(self, api_key: str):
        if api_key:
            try:
                self.groq_client = Groq(api_key=api_key)
            except Exception as e:
                print(f"⚠️ Failed to initialize Groq client: {e}")
                self.groq_client = None
        else:
            print("⚠️ Groq API key not provided.")
            self.groq_client = None

        self._call_count = 0
        self._last_call_time = 0.0

    @property
    def _llm_type(self) -> str:
        return "groq"

    def _call(self, prompt: str, stop: Optional[List[str]] = None, **kwargs) -> str:
        """Call the Groq API with rate limiting and error handling."""
        if not self.groq_client:
            return f"Groq client not available. Using fallback analysis for prompt: {prompt[:100]}..."

        current_time = time.time()
        if current_time - self._last_call_time < 1.0:
            time.sleep(1.0)

        self._last_call_time = time.time()
        self._call_count += 1

        try:
            response = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                **kwargs
            )

            result = response.choices[0].message.content

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
            else:
                return f"Analysis Error: {error_msg}"