"""Service for text summarization using AI providers."""

from pathlib import Path

from django.conf import settings
from pydantic import BaseModel

from .models import SummaryItem
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

    def summarize(
        self,
        text: str,
        prompt: str | None = None,
        result_type: type[BaseModel] = SummaryItem,
    ) -> BaseModel:
        """
        Summarize text.

        Args:
            text: Text to summarize
            prompt: Optional custom prompt (default prompt will be used if not provided)
            result_type: Pydantic BaseModel class for structured output (default: SummaryItem)

        Returns:
            Structured response as BaseModel instance

        Raises:
            Exception: If summarization fails
        """
        request = SummaryRequest(text=text, prompt=prompt)
        response = self.provider.request(request, result_type=result_type)
        return response

    def multimodal_summarize(
        self,
        doc_path: str | Path,
        text: str | None = None,
        prompt: str | None = None,
        result_type: type[BaseModel] = SummaryItem,
    ) -> BaseModel:
        """
        Summarize a document/image using vision API.

        Args:
            doc_path: Path to the document/image file
            text: Optional text to include in the analysis
            prompt: Optional custom prompt (default prompt will be used if not provided)
            result_type: Pydantic BaseModel class for structured output (default: SummaryItem)

        Returns:
            Structured response as BaseModel instance

        Raises:
            Exception: If summarization fails
        """
        doc_path = Path(doc_path)
        if not doc_path.exists():
            raise FileNotFoundError(f"Document file not found: {doc_path}")

        request = MultimodalSummaryRequest(doc_path=doc_path, text=text, prompt=prompt)
        response = self.provider.multimodal_request(
            request, result_type=result_type, doc_path=doc_path
        )
        return response


class SummaryRequest(AIRequest):
    """Request model for text summarization."""

    DEFAULT_PROMPT = (
        "Fasse den folgenden Text zusammen. "
        "Gib deine Antwort als strukturiertes JSON zurück, das dem erwarteten Format entspricht."
    )

    def __init__(self, text: str, prompt: str | None = None) -> None:
        super().__init__()
        self.text = text
        self.prompt_text = prompt or self.DEFAULT_PROMPT

    def prompt(self) -> str:
        return f"{self.prompt_text}\n\n{self.text}"


class MultimodalSummaryRequest(AIRequest):
    """Request model for multimodal document summarization."""

    DEFAULT_PROMPT = (
        "Fasse dieses Dokument/Bild zusammen. "
        "Beschreibe den Inhalt und die wichtigsten Informationen. "
        "Gib deine Antwort als strukturiertes JSON zurück, das dem erwarteten Format entspricht."
    )

    def __init__(
        self, doc_path: str | Path, text: str | None = None, prompt: str | None = None
    ) -> None:
        super().__init__()
        self.doc_path = Path(doc_path)
        self.prompt_text = prompt or self.DEFAULT_PROMPT
        self.text = text

    def prompt(self) -> str:
        if self.text:
            return self.prompt_text + "\n\nText:\n" + self.text
        return self.prompt_text
