"""Service for text summarization using AI providers."""

from django.conf import settings

from .providers import AIProvider
from .providers import ProviderConfig
from .providers import SummaryRequest


class SummarizationService:
    """Service for summarizing text using configured AI provider."""

    def __init__(self, provider_handle: str = None):
        """
        Initialize summarization service.

        Args:
            provider_handle: Optional provider handle to override settings
        """
        provider_handle = provider_handle or getattr(
            settings, "SUMMARIZATION_PROVIDER_HANDLE", "openrouter"
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
        response = self.provider.summarize(request)
        return response.summary
