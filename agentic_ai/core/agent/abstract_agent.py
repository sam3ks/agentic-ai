# abstract_agent.py
from abc import ABC, abstractmethod

class AbstractAgent(ABC):
    """Abstract base class for all agents."""

    @abstractmethod
    def run(self, **kwargs) -> str:
        """Runs the agent's specific task."""
        pass
