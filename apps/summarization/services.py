"""Service for text summarization using AI providers."""

import json
from pathlib import Path

from django.conf import settings
from pydantic import BaseModel

from .models import ProjectSummary
from .providers import AIProvider
from .providers import AIRequest
from .providers import ProviderConfig
from .pydantic_models import SummaryItem
from .pydantic_models import SummaryResponse


class AIService:
    """Service for summarizing text using configured AI provider."""

    def __init__(self, provider_handle: str = None):
        """Initialize AI service."""
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
        """Summarize text."""
        request = SummaryRequest(text=text, prompt=prompt)
        response = self.provider.request(request, result_type=result_type)
        return response

    def project_summarize(
        self,
        project,
        text: str,
        prompt: str | None = None,
        result_type: type[BaseModel] = SummaryResponse,
    ) -> BaseModel:
        """Summarize text for a project with caching support."""
        request = SummaryRequest(text=text, prompt=prompt)

        # Check cache
        cached = ProjectSummary.get_cached_summary(
            project=project,
            prompt=request.prompt_text,
            input_text=text,
        )
        if cached:
            print("****** Cached summary found ******")
            return SummaryResponse(**cached.response_data)

        # Generate new summary
        response = self.provider.request(request, result_type=result_type)

        # Save to cache if result is SummaryResponse
        if isinstance(response, SummaryResponse):
            ProjectSummary.objects.create(
                project=project,
                prompt=request.prompt_text,
                input_text_hash=ProjectSummary.compute_hash(text),
                response_data=json.loads(response.model_dump_json()),
            )

        return response

    def multimodal_summarize(
        self,
        doc_path: str | Path,
        text: str | None = None,
        prompt: str | None = None,
        result_type: type[BaseModel] = SummaryItem,
    ) -> BaseModel:
        """Summarize a document/image using vision API."""
        request = MultimodalSummaryRequest(doc_path=doc_path, text=text, prompt=prompt)
        response = self.provider.multimodal_request(
            request, result_type=result_type, doc_path=doc_path
        )
        return response


class SummaryRequest(AIRequest):
    """Request model for text summarization."""

    DEFAULT_PROMPT = (
        "Summarize the following text. "
        "Return your answer as structured JSON that matches the expected format. "
        "Create multiple summary_items and module_items if relevant."
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
        "Summarize this document/image. "
        "Describe the content and the most important information. "
        "Return your answer as structured JSON that matches the expected format."
    )

    def __init__(
        self, doc_path: str | Path, text: str | None = None, prompt: str | None = None
    ) -> None:
        super().__init__()
        self.doc_path = Path(doc_path)
        if not self.doc_path.exists():
            raise FileNotFoundError(f"Document file not found: {self.doc_path}")
        self.prompt_text = prompt or self.DEFAULT_PROMPT
        self.text = text

    def prompt(self) -> str:
        if self.text:
            return self.prompt_text + "\n\nText:\n" + self.text
        return self.prompt_text
