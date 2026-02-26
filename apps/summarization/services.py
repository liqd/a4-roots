"""Service for text summarization using AI providers."""

import json
import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from pydantic import BaseModel
from sentry_sdk import capture_exception

from .models import ProjectSummary
from .providers import AIProvider
from .providers import AIRequest
from .providers import ProviderConfig
from .pydantic_models import DocumentInputItem
from .pydantic_models import DocumentSummaryItem
from .pydantic_models import DocumentSummaryResponse
from .pydantic_models import ProjectSummaryResponse
from .pydantic_models import SummaryItem
from .utils import extract_text_from_document

logger = logging.getLogger(__name__)


# Rate limits (can be moved to settings)
PROJECT_SUMMARY_RATE_LIMIT_MINUTES = getattr(
    settings, "PROJECT_SUMMARY_RATE_LIMIT_MINUTES", 5
)
SUMMARY_GLOBAL_LIMIT_PER_HOUR = getattr(settings, "SUMMARY_GLOBAL_LIMIT_PER_HOUR", 100)
FALLBACK_MAX_AGE_MINUTES = getattr(
    settings, "PROJECT_SUMMARY_FALLBACK_MAX_AGE_MINUTES", 0
)


class AIService:
    """Service for summarizing text using configured AI provider."""

    def __init__(
        self, provider_handle: str = None, document_provider_handle: str = None
    ):
        """Initialize AI service with providers."""
        self.provider = self._init_provider(provider_handle, "AI_PROVIDER")
        self.document_provider = self._init_provider(
            document_provider_handle, "AI_DOCUMENT_PROVIDER"
        )

    def _init_provider(self, handle: str | None, settings_key: str) -> AIProvider:
        """Initialize a provider from handle or settings."""
        if not handle:
            handle = getattr(settings, settings_key, None)
            if not handle:
                raise ValueError(
                    f"No provider configured. Pass {settings_key.lower()} or set {settings_key} in settings."
                )
        return AIProvider(ProviderConfig.from_handle(handle))

    def summarize(
        self,
        text: str,
        prompt: str | None = None,
        result_type: type[BaseModel] = SummaryItem,
    ) -> BaseModel:
        """Summarize text."""
        request = SummaryRequest(text=text, prompt=prompt)
        return self.provider.request(request, result_type=result_type)

    def project_summarize(
        self,
        project,
        text: str,
        prompt: str | None = None,
        result_type: type[BaseModel] = ProjectSummaryResponse,
        skip_cache: bool = False,
    ) -> BaseModel:
        """Summarize project data with caching."""
        request = SummaryRequest(text=text, prompt=prompt)
        latest = self._get_latest_summary(project)

        # Try cache if not skipped
        if not skip_cache:
            cached = self._get_cached_response(project, text, latest)
            if cached:
                return cached

        # Generate new summary
        logger.info(f"Generating summary for project {project.id} ({project.slug})")

        try:
            response = self.provider.request(request, result_type=result_type)
            self._save_to_cache(project, request.prompt_text, text, response)
            return response
        except Exception as e:
            logger.error(f"Summary generation failed: {e}", exc_info=True)
            capture_exception(e)

            fallback = self._get_fallback_response(latest)
            if fallback:
                return fallback
            raise

    def _get_latest_summary(self, project):
        """Get most recent summary for project."""
        return (
            ProjectSummary.objects.filter(project=project)
            .order_by("-created_at")
            .first()
        )

    def _get_cached_response(
        self, project, text: str, latest
    ) -> ProjectSummaryResponse | None:
        """Return cached response if valid."""
        if not latest:
            return None

        # Exact match
        if latest.input_text_hash == ProjectSummary.compute_hash(text):
            logger.debug(f"Cache hit (exact match) for project {project.id}")
            return ProjectSummaryResponse(**latest.response_data)

        # Rate limit checks
        age = timezone.now() - latest.created_at

        if age < timedelta(minutes=PROJECT_SUMMARY_RATE_LIMIT_MINUTES):
            logger.debug(f"Using rate-limited cache for project {project.id}")
            return ProjectSummaryResponse(**latest.response_data)

        if age < timedelta(hours=1):
            recent = ProjectSummary.objects.filter(
                created_at__gte=timezone.now() - timedelta(hours=1)
            ).count()
            if recent >= SUMMARY_GLOBAL_LIMIT_PER_HOUR:
                logger.debug(
                    f"Global rate limit reached, using cache for project {project.id}"
                )
                return ProjectSummaryResponse(**latest.response_data)

        return None

    def _get_fallback_response(self, latest) -> ProjectSummaryResponse | None:
        """Return cached response as fallback if within age limit."""
        if FALLBACK_MAX_AGE_MINUTES == 0 or not latest:
            return None

        age = (timezone.now() - latest.created_at).total_seconds() / 60
        if age <= FALLBACK_MAX_AGE_MINUTES:
            logger.debug(f"Using fallback cache (age: {age:.1f} min)")
            return ProjectSummaryResponse(**latest.response_data)

        return None

    def _save_to_cache(self, project, prompt: str, text: str, response: BaseModel):
        """Save successful response to cache."""
        if isinstance(response, ProjectSummaryResponse):
            ProjectSummary.objects.create(
                project=project,
                prompt=prompt,
                input_text_hash=ProjectSummary.compute_hash(text),
                response_data=json.loads(response.model_dump_json()),
            )
            logger.info(f"Cached summary for project {project.id}")

    def request_vision_dict(
        self, documents_dict: dict[str, str], prompt: str | None = None
    ) -> DocumentSummaryResponse:
        """Process documents from dictionary format."""
        items = [DocumentInputItem(handle=h, url=u) for h, u in documents_dict.items()]
        return self.request_vision(items, prompt)

    def request_vision(
        self, documents: list[DocumentInputItem], prompt: str | None = None
    ) -> DocumentSummaryResponse:
        """Process documents and images, return combined summaries."""
        docs, images = self._split_documents(documents)

        results = []
        if docs[0]:
            results.extend(self._process_documents(docs))
        if images[0]:
            results.extend(self._process_images(images, prompt))

        return DocumentSummaryResponse(documents=results)

    def _split_documents(self, documents):
        """Split into regular docs and images."""
        docs_urls, docs_handles = [], []
        img_urls, img_handles = [], []

        for doc in documents:
            if (
                not self.document_provider.config.supports_documents
                and doc.is_document()
            ):
                docs_urls.append(doc.url)
                docs_handles.append(doc.handle)
            else:
                img_urls.append(doc.url)
                img_handles.append(doc.handle)

        return (docs_urls, docs_handles), (img_urls, img_handles)

    def _process_documents(self, docs_data):
        """Extract text from PDFs/DOCX files."""
        urls, handles = docs_data
        results = []

        for url, handle in zip(urls, handles):
            try:
                text = extract_text_from_document(url)
                results.append(DocumentSummaryItem(handle=handle, summary=text))
            except Exception as e:
                logger.error(
                    f"Failed to extract text from {handle}: {e}", exc_info=True
                )
                capture_exception(e)

        return results

    def _process_images(self, images_data, prompt):
        """Process images with vision API."""
        urls, handles = images_data

        if not prompt:
            prompt = (
                f"Summarize each image separately. Handles in order: {handles}. "
                f"Return list of summaries with handles."
            )

        request = MultimodalSummaryRequest(image_urls=urls, prompt=prompt)
        response = self.document_provider.request(request, DocumentSummaryResponse)
        return response.documents


class SummaryRequest(AIRequest):
    """Request model for text summarization."""

    DEFAULT_PROMPT = """
You are a JSON generator. Return ONLY valid JSON.

Schema:
{
  "title": "Summary of participation",
  "general_info": {"summary": "string", "goals": ["string"]},
  "phases": {
    "past": {"modules": [{"module_name": "string", "status": "past", "final": {"summary": "string", "bullets": ["string"]}, "debug": {...}}]},
    "current": {"modules": [{"module_name": "string", "status": "current", "final": {"summary": "string", "bullets": ["string"]}, "debug": {...}}]},
    "upcoming": {"modules": [{"module_name": "string", "status": "upcoming", "final": {"summary": "string", "bullets": ["string"]}, "debug": {...}}]}
  }
}

Each module MUST include a 'debug' object with:
- module_type: string
- signals_snapshot: list of strings
- draft_before_qa: string
- claims: list of {claim_text, evidence_type(from_votes|from_ratings|from_open_answers|from_comments|from_base_text|uncertain), action(keep|soften|remove), fix_hint}
- quantifier_fixes: list of {original_phrase, replacement, reason}
- anchors: list of strings
- coverage_gaps: list of strings
- coverage_patch: optional string
- patches: list of {patch_type(REPLACE|REMOVE|ADD_SENTENCE), target, replacement}
- after_qa: string
- diff_summary: optional string
- qa_status: PASS|FAIL

Extract real data from the project export.
Respond with ONLY the JSON object.
"""

    def __init__(self, text: str, prompt: str | None = None):
        super().__init__()
        self.text = text
        self.prompt_text = prompt or self.DEFAULT_PROMPT

    def prompt(self) -> str:
        return f"{self.prompt_text}\n\n{self.text}"


class MultimodalSummaryRequest(AIRequest):
    """Request model for multimodal document summarization."""

    vision_support = True
    PROMPT = "Summarize this image/document. Return JSON with summary field."

    def __init__(
        self, image_urls: list[str], text: str | None = None, prompt: str | None = None
    ):
        super().__init__()
        self.image_urls = image_urls
        self.prompt_text = prompt or self.PROMPT
        self.text = text

    def prompt(self) -> str:
        base = self.prompt_text
        return f"{base}\n\nText:\n{self.text}" if self.text else base


class DocumentRequest(AIRequest):
    """Request model for document summarization."""

    vision_support = True
    PROMPT = "Summarize this document. Return JSON with summary field."

    def __init__(self, url: str, prompt: str | None = None):
        super().__init__()
        self.image_urls = [url]
        self.prompt_text = prompt or self.PROMPT

    def prompt(self) -> str:
        return self.prompt_text
