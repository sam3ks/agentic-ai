from abc import ABC, abstractmethod
from typing import List, Optional

class BaseLLM(ABC):
    """Abstract base class for all LLM implementations."""

    @abstractmethod
    def _call(self, prompt: str, stop: Optional[List[str]] = None, **kwargs) -> str:
        """Execute the LLM call with the given prompt."""
        pass

    @property
    @abstractmethod
    def _llm_type(self) -> str:
        """Return the type of LLM (e.g., 'groq', 'openai')."""
        pass