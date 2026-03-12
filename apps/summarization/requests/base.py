"""Base classes for AI requests."""

from abc import ABC
from abc import abstractmethod


class AIRequest(ABC):
    """Base class for all AI requests."""

    vision_support = False

    @abstractmethod
    def prompt(self) -> str:
        """Return the prompt text for this request."""
        pass
