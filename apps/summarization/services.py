"""Service for text summarization using AI providers."""

from pathlib import Path

from django.conf import settings
from pydantic import BaseModel
from pydantic import Field

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

    def summarize(self, text: str) -> str:
        """
        Summarize text.

        Args:
            text: Text to summarize

        Returns:
            Summarized text

        Raises:
            Exception: If summarization fails
        """
        request = SummaryRequest(text=text)
        response = self.provider.request(request, result_type=SummaryResponse)
        return response.summary

    def multimodal_summarize(self, doc_path: str | Path) -> str:
        """
        Summarize a document/image using vision API.

        Args:
            doc_path: Path to the document/image file

        Returns:
            Summarized text

        Raises:
            Exception: If summarization fails
        """
        doc_path = Path(doc_path)
        if not doc_path.exists():
            raise FileNotFoundError(f"Document file not found: {doc_path}")

        request = MultimodalSummaryRequest(doc_path=doc_path)
        response = self.provider.multimodal_request(
            request, result_type=SummaryResponse, doc_path=doc_path
        )
        return response.summary


class SummaryRequest(AIRequest):

    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text

    def prompt(self) -> str:
        return f"Fasse den folgenden Text zusammen:\n\n{self.text}"


class MultimodalSummaryRequest(AIRequest):
    """Request model for multimodal document summarization."""

    def __init__(self, doc_path: str | Path) -> None:
        super().__init__()
        self.doc_path = Path(doc_path)

    def prompt(self) -> str:
        return (
            "Fasse dieses Dokument/Bild zusammen. "
            "Beschreibe den Inhalt und die wichtigsten Informationen. "
            "Gib deine Antwort als strukturierte Zusammenfassung zurück."
        )


class SummaryResponse(BaseModel):
    """Response model for summarization."""

    summary: str = Field(description="Die Zusammenfassung des Textes oder Bildes")
    key_points: list[str] = Field(
        default_factory=list,
        description="Wichtige Punkte oder Stichworte aus dem Text oder Bild",
    )
    provider: str = Field(default="", description="Provider name (set automatically)")
