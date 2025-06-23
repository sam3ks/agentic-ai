from agentic_ai.core.config.loader import LangChainLLMWrapper
from agentic_ai.core.agent.abstract_agent import AbstractAgent

class BaseAgent(AbstractAgent):
    """Base class for agents utilizing an LLM."""

    def __init__(self):
        self.llm = LangChainLLMWrapper()

    def run(self, **kwargs) -> str:
        raise NotImplementedError("Each agent must implement its own run method.")