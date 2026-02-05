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

    def summarize_image(self, image_path: str | Path, max_length: int = 500) -> str:
        """
        Summarize an image using vision API.

        Args:
            image_path: Path to the image file
            max_length: Maximum length of summary in characters

        Returns:
            Summarized text

        Raises:
            Exception: If summarization fails
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        request = ImageSummaryRequest(image_path=image_path, max_length=max_length)
        response = self.provider.request_with_image(
            request, result_type=SummaryResponse, image_paths=[image_path]
        )
        return response.summary


class SummaryRequest(AIRequest):

    def __init__(self, text: str, max_length: int = 500) -> None:
        super().__init__()
        self.text = text
        self.max_length = max_length

    def prompt(self) -> str:
        return f"Fasse den folgenden Text in maximal {self.max_length} Zeichen zusammen:\n\n{self.text}"


class ImageSummaryRequest(AIRequest):
    """Request model for image summarization."""

    def __init__(self, image_path: str | Path, max_length: int = 500) -> None:
        super().__init__()
        self.image_path = Path(image_path)
        self.max_length = max_length

    def prompt(self) -> str:
        return (
            f"Fasse dieses Bild in maximal {self.max_length} Zeichen zusammen. "
            f"Beschreibe den Inhalt und die wichtigsten Informationen. "
            f"Gib deine Antwort als strukturierte Zusammenfassung zurück."
        )


class SummaryResponse(BaseModel):
    """Response model for summarization."""

    summary: str = Field(description="Die Zusammenfassung des Textes oder Bildes")
    key_points: list[str] = Field(
        default_factory=list,
        description="Wichtige Punkte oder Stichworte aus dem Text oder Bild"
    )
    provider: str = Field(default="", description="Provider name (set automatically)")
