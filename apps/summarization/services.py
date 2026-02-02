"""Service for text summarization using AI providers."""

from django.conf import settings
from pydantic import BaseModel

from .providers import AIProvider
from .providers import AIRequest
from .providers import ProviderConfig


class AIService:
    """Service for summarizing text using configured AI provider."""

    def __init__(self, provider_handle: str = None):
        """
        Initialize AI service.

        Args:
            provider_handle: Optional provider handle to override settings
        """
        provider_handle = provider_handle or getattr(
            settings, "AI_PROVIDER", "openrouter"
        )
        # ProviderConfig loads configuration from settings automatically
        config = ProviderConfig.from_handle(provider_handle)
        self.provider = AIProvider(config)

    def summarize(self, text: str, max_length: int = 500) -> str:
        """
        Summarize text.

        Args:
            text: Text to summarize
            max_length: Maximum length of summary in characters

        Returns:
            Summarized text

        Raises:
            Exception: If summarization fails
        """
        request = SummaryRequest(text=text, max_length=max_length)
        response = self.provider.request(request, result_type=SummaryResponse)
        return response.summary


class SummaryRequest(AIRequest):

    def __init__(self, text: str, max_length: int = 500) -> None:
        super().__init__()
        self.text = text
        self.max_length = max_length

    def prompt(self) -> str:
        return f"Fasse den folgenden Text in maximal {self.max_length} Zeichen zusammen:\n\n{self.text}"


class SummaryResponse(BaseModel):
    """Response model for summarization."""

    summary: str
    provider: str
