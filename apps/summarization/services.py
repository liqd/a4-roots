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


PROJECT_SUMMARY_RATE_LIMIT_MINUTES = (
    5  # Minimum minutes between summary generations per project
)
SUMMARY_GLOBAL_LIMIT_PER_HOUR = 100  # Maximum summaries per hour across all projects


class ProjectSummarizeMixin:
    """Mixin to add show_debug support to project_summarize."""

    def project_summarize(
        self,
        project,
        text: str,
        prompt: str | None = None,
        result_type: type[BaseModel] = ProjectSummaryResponse,
        is_rate_limit: bool = True,
        show_debug: bool = False,  # Add this parameter
    ) -> BaseModel:
        """Summarize text for a project with caching and rate limiting support."""
        request = SummaryRequest(text=text, prompt=prompt, show_debug=show_debug)
        latest_project_summary = (
            ProjectSummary.objects.filter(project=project)
            .order_by("-created_at")
            .first()
        )

        # Check cache and rate limits
        # if is_rate_limit:
        #     cached_response = self._check_cache_and_rate_limits(
        #         project, text, latest_project_summary
        #     )
        #     if cached_response:
        #         return cached_response

        # Generate new summary
        logger.info(
            f"Generating new summary for project {project.id} ({project.slug})"
            + (" with debug" if show_debug else "")
        )
        logger.debug(f"Prompt preview: {request.prompt()[:500]}...")

        try:
            response = self.provider.request(request, result_type=result_type)

            if isinstance(response, ProjectSummaryResponse):
                logger.info(
                    f"Created new project summary for project {project.id} ({project.slug})"
                )
                ProjectSummary.objects.create(
                    project=project,
                    prompt=request.prompt_text,
                    input_text_hash=ProjectSummary.compute_hash(text),
                    response_data=json.loads(response.model_dump_json()),
                )
            return response

        except Exception as e:
            logger.error(
                f"Error during summary generation for project {project.id} ({project.slug}): {str(e)} - NOT CACHING",
                exc_info=True,
            )
            capture_exception(e)
            fallback_response = self._try_fallback_cache(latest_project_summary)
            if fallback_response:
                logger.info(
                    f"Using fallback cache for project {project.id} after error"
                )
                return fallback_response
            logger.warning(
                f"Re-raising exception - no valid fallback available for project {project.id}"
            )
            raise


class AIService(ProjectSummarizeMixin):
    """Service for summarizing text using configured AI provider."""

    def __init__(
        self, provider_handle: str = None, document_provider_handle: str = None
    ):
        """Initialize AI service."""
        # Check if provider_handle is provided or configured in settings
        if not provider_handle:
            provider_handle = getattr(settings, "AI_PROVIDER", None)
            if not provider_handle:
                raise ValueError(
                    "No provider configured. "
                    "Either pass provider_handle to AIService() or set AI_PROVIDER in settings."
                )

        # ProviderConfig loads configuration from settings automatically
        config = ProviderConfig.from_handle(provider_handle)
        self.provider = AIProvider(config)

        # Check if document_provider_handle is provided or configured in settings
        if not document_provider_handle:
            document_provider_handle = getattr(settings, "AI_DOCUMENT_PROVIDER", None)
            if not document_provider_handle:
                raise ValueError(
                    "No document provider configured. "
                    "Either pass document_provider_handle to AIService() or set AI_DOCUMENT_PROVIDER in settings."
                )

        doc_config = ProviderConfig.from_handle(document_provider_handle)
        self.document_provider = AIProvider(doc_config)

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

    def _check_cache_and_rate_limits(
        self, project, text: str, latest_project_summary
    ) -> ProjectSummaryResponse | None:
        """Check cache and rate limits, return cached summary if applicable."""
        if not latest_project_summary:
            return None

        # Check 1: Exact content match
        current_hash = ProjectSummary.compute_hash(text)
        if latest_project_summary.input_text_hash == current_hash:
            logger.debug(
                f"Cached summary found (exact match via hash comparison) for project {project.id}"
            )
            return ProjectSummaryResponse(**latest_project_summary.response_data)

        # Check 2: Per-project rate limiting
        time_since_last = timezone.now() - latest_project_summary.created_at
        if time_since_last < timedelta(minutes=PROJECT_SUMMARY_RATE_LIMIT_MINUTES):
            logger.debug(
                f"Using rate-limited summary from {latest_project_summary.created_at} "
                f"(within {PROJECT_SUMMARY_RATE_LIMIT_MINUTES} min per project) for project {project.id}"
            )
            return ProjectSummaryResponse(**latest_project_summary.response_data)

        # Check 3: Global rate limiting
        if time_since_last < timedelta(hours=1):
            global_limit_time = timezone.now() - timedelta(hours=1)
            recent_global_count = ProjectSummary.objects.filter(
                created_at__gte=global_limit_time
            ).count()

            if recent_global_count >= SUMMARY_GLOBAL_LIMIT_PER_HOUR:
                logger.debug(
                    f"Global rate limit reached ({recent_global_count}/{SUMMARY_GLOBAL_LIMIT_PER_HOUR} in last hour), "
                    f"using most recent summary from {latest_project_summary.created_at} for project {project.id}"
                )
                return ProjectSummaryResponse(**latest_project_summary.response_data)

        return None

    def _try_fallback_cache(
        self, latest_project_summary
    ) -> ProjectSummaryResponse | None:
        """Try to use cached fallback on error."""
        fallback_max_age_minutes = getattr(
            settings, "PROJECT_SUMMARY_FALLBACK_MAX_AGE_MINUTES", 0
        )
        logger.debug(
            f"Fallback check: max_age_minutes={fallback_max_age_minutes}, "
            f"latest_project_summary exists={latest_project_summary is not None}"
        )

        if fallback_max_age_minutes == 0:
            logger.debug("Fallback disabled (max_age_minutes=0)")
            return None

        if not latest_project_summary:
            logger.debug("No cached summary available for fallback")
            return None

        time_since_cached = timezone.now() - latest_project_summary.created_at
        max_age = timedelta(minutes=fallback_max_age_minutes)
        age_minutes = time_since_cached.total_seconds() / 60

        logger.debug(
            f"Fallback age check: {age_minutes:.1f} min <= {fallback_max_age_minutes} min? "
            f"{age_minutes <= fallback_max_age_minutes}"
        )

        if time_since_cached <= max_age:
            logger.debug(
                f"Using cached fallback summary from {latest_project_summary.created_at} "
                f"(age: {age_minutes:.1f} min, max: {fallback_max_age_minutes} min)"
            )
            return ProjectSummaryResponse(**latest_project_summary.response_data)
        else:
            logger.debug(
                f"Cached summary too old ({age_minutes:.1f} min > {fallback_max_age_minutes} min) - not using fallback"
            )
        return None

    def request_vision(
        self,
        documents: list[DocumentInputItem],
        prompt: str | None = None,
    ) -> DocumentSummaryResponse:
        """Process documents and images, return combined summaries."""
        document_urls = []
        document_handle_list = []
        image_urls = []
        image_handle_list = []

        for doc in documents:
            if (
                not self.document_provider.config.supports_documents
                and doc.is_document()
            ):
                document_urls.append(doc.url)
                document_handle_list.append(doc.handle)
            else:
                image_urls.append(doc.url)
                image_handle_list.append(doc.handle)

        document_results = []
        if document_urls:
            results1 = self.request_documents(document_urls, document_handle_list)
            document_results = results1.documents

        image_results = []
        if image_urls:
            results2 = self.request_images(image_urls, image_handle_list, prompt)
            image_results = results2.documents

        return DocumentSummaryResponse(documents=image_results + document_results)

    def request_vision_dict(
        self,
        documents_dict: dict[str, str],
        prompt: str | None = None,
    ) -> DocumentSummaryResponse:
        """
        Process documents from dictionary format.

        Args:
            documents_dict: Dictionary mapping handles to absolute URLs
            prompt: Optional prompt for summarization

        Returns:
            DocumentSummaryResponse with summaries for all documents
        """
        document_items = [
            DocumentInputItem(handle=handle, url=url)
            for handle, url in documents_dict.items()
        ]
        return self.request_vision(documents=document_items, prompt=prompt)

    def request_images(
        self,
        image_urls: list[str],
        image_handle_list: list[str],
        prompt: str | None = None,
    ) -> DocumentSummaryResponse:
        if prompt:
            custom_prompt = prompt
        else:
            custom_prompt = (
                f"Summarize each document separately. "
                f"The documents are provided in order with the following handles: {image_handle_list}. "
                f"Return a list of summaries, one for each document in the same order. "
                f"Each summary should include the handle and describe the content and most important information of that document."
            )

        request = MultimodalSummaryRequest(
            image_urls=image_urls,
            prompt=custom_prompt,
        )
        return self.document_provider.request(
            request, result_type=DocumentSummaryResponse
        )

    def request_documents(
        self,
        document_urls: list[str],
        document_handle_list: list[str],
    ) -> DocumentSummaryResponse:
        """Extract text from PDFs and DOCX files, return as summaries."""
        results = []

        for url, handle in zip(document_urls, document_handle_list):
            try:
                extracted_text = extract_text_from_document(url)
                results.append(
                    DocumentSummaryItem(handle=handle, summary=extracted_text)
                )
            except Exception as e:
                logger.error(
                    f"Failed to extract text from document {handle} ({url}): {str(e)}",
                    exc_info=True,
                )
                capture_exception(e)

        return DocumentSummaryResponse(documents=results)


# TODO: Move to a providers.py ?


class SummaryRequest(AIRequest):
    """Request model for text summarization."""

    DEFAULT_PROMPT = """
        You are a JSON generator. Return ONLY valid JSON. No explanations, no markdown, no code blocks.

        Schema:
        {
          "title": "Summary of participation",
          "general_info": {
            "summary": "A concise overview of the entire project and its participation process",
            "goals": ["Goal 1", "Goal 2", "Goal 3"]
          },
          "phases": {
            "past": {
              "modules": [
                {
                  "module_name": "Name of the completed module",
                  "status": "past",
                  "final": {
                    "summary": "Summary of what happened in this module, including key outcomes",
                    "bullets": ["Key point 1", "Key point 2", "Key point 3"]
                  }
                }
              ]
            },
            "current": {
              "modules": [
                {
                  "module_name": "Name of the active module",
                  "status": "current",
                  "final": {
                    "summary": "Summary of what's happening in this module now",
                    "bullets": ["Current key point 1", "Current key point 2"]
                  }
                }
              ]
            },
            "upcoming": {
              "modules": [
                {
                  "module_name": "Name of the upcoming module",
                  "status": "upcoming",
                  "final": {
                    "summary": "What will happen in this module",
                    "bullets": ["Planned activity 1", "Planned activity 2"]
                  }
                }
              ]
            }
          }
        }

        Extract real data from the project export. For past modules, focus on outcomes and main sentiments.
        For current modules, focus on ongoing activities and early content.
        For upcoming modules, focus on planned activities and goals.
        Respond with ONLY the JSON object.
        """

    def __init__(
        self, text: str, prompt: str | None = None, show_debug: bool = False
    ) -> None:
        super().__init__()
        self.text = text
        self.show_debug = show_debug
        self.prompt_text = prompt or self.DEFAULT_PROMPT

        if show_debug:
            self.prompt_text += """
        IMPORTANT: Include debug information in the response following the full schema with 'show_debug': true.
        Each module should include a 'debug' object with:
        - module_type: the type of module
        - signals_snapshot: list of signals present (e.g., ["has_comments", "has_votes"])
        - draft_before_qa: initial summary draft before QA
        - claims: list of objects with:
            * claim_text: string
            * evidence_type: MUST be one of: "from_votes", "from_ratings", "from_open_answers", "from_comments", "from_base_text", or "uncertain" (no other values allowed)
            * action: MUST be one of: "keep", "soften", or "remove" (no other values allowed)
            * fix_hint: optional string
        - quantifier_fixes: list of objects with original_phrase, replacement, reason
        - anchors: list of key data points referenced
        - coverage_gaps: list of topics that should have been covered but weren't
        - coverage_patch: optional text to fix coverage gaps
        - patches: list of objects with patch_type (REPLACE|REMOVE|ADD_SENTENCE), target, replacement
        - after_qa: final summary after QA
        - diff_summary: optional summary of changes made
        - qa_status: MUST be either "PASS" or "FAIL" (no other values allowed)
        """

    def prompt(self) -> str:
        return f"{self.prompt_text}\n\n{self.text}"


# TODO: Move to a providers.py ?


class MultimodalSummaryRequest(AIRequest):
    """Request model for multimodal document summarization."""

    vision_support = True

    DEFAULT_PROMPT = (
        "Summarize this document/image. "
        "Describe the content and the most important information. "
        "Return your answer as structured JSON that matches the expected format."
    )

    def __init__(
        self,
        image_urls: list[str] | None = None,
        text: str | None = None,
        prompt: str | None = None,
    ) -> None:
        super().__init__()
        self.image_urls = image_urls or []
        self.prompt_text = prompt or self.DEFAULT_PROMPT
        self.text = text

    def prompt(self) -> str:
        if self.text:
            return self.prompt_text + "\n\nText:\n" + self.text
        return self.prompt_text


class DocumentRequest(AIRequest):
    """Request model for document summarization with handle."""

    vision_support = True

    DEFAULT_PROMPT = (
        "Summarize this document. "
        "Describe the content and the most important information. "
        "Return your answer as structured JSON with 'summary' field, "
    )

    def __init__(
        self,
        url: str,
        prompt: str | None = None,
    ) -> None:
        super().__init__()
        self.image_urls = [url]
        self.prompt_text = prompt or self.DEFAULT_PROMPT

    def prompt(self) -> str:
        return self.prompt_text
