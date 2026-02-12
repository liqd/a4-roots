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
from .pydantic_models import ProjectSummaryResponse 

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
        result_type: type[BaseModel] = ProjectSummaryResponse,  # Changed from SummaryResponse
    ) -> BaseModel:
        """Summarize text for a project with caching support."""
        request = SummaryRequest(text=text, prompt=prompt)

        # Cache disabled for dev work

        # # Check cache
        # cached = ProjectSummary.get_cached_summary(
        #     project=project,
        #     prompt=request.prompt_text,
        #     input_text=text,
        # )
        # if cached:
        #     print("****** Cached summary found ******")
        #     return ProjectSummaryResponse(**cached.response_data)  # Changed

        # Generate new summary
        print("****** Generating new summary ******")
        print(f"Prompt: {request.prompt()[:500]}...")

        response = self.provider.request(request, result_type=result_type)

        # Save to cache if result is ProjectSummaryResponse
        if isinstance(response, ProjectSummaryResponse):  # Changed
            print(" ------------------ >>>>>>>>>>. CREATED THE PROJECT SUMMARY")
            ProjectSummary.objects.create(
                project=project,
                prompt=request.prompt_text,
                input_text_hash=ProjectSummary.compute_hash(text),
                response_data=json.loads(response.model_dump_json()),
            )
        return response

class SummaryRequest(AIRequest):
    """Request model for text summarization."""
    
    DEFAULT_PROMPT = """
        You are a JSON generator. Return ONLY valid JSON. No explanations, no markdown, no code blocks.
        
        Schema:
        {
        "title": "Zusammenfassung der Beteiligung",
        "stats": {"participants": 0, "contributions": 0, "modules": 0},
        "past_summary": "string",
        "past_modules": [
            {
            "module_name": "string",
            "purpose": "string",
            "main_sentiments": ["string"],
            "phase_status": "past",
            "link": "string"
            }
        ],
        "current_summary": "string",
        "current_modules": [
            {
            "module_name": "string",
            "purpose": "string",
            "main_sentiments": ["string"],
            "first_content": "string",
            "phase_status": "active",
            "link": "string"
            }
        ],
        "upcoming_summary": "string",
        "upcoming_modules": [
            {
            "module_name": "string",
            "purpose": "string",
            "phase_status": "upcoming",
            "link": "string"
            }
        ]
        }
        
        Extract real data from the project export. Use actual numbers and content.
        Respond with ONLY the JSON object.
        """
    
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
