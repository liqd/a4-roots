"""Project summarization service."""

import logging

from django.conf import settings
from sentry_sdk import capture_exception

from ..models import ProjectSummary
from ..pydantic_models import ProjectSummaryResponse
from ..requests.project import SummaryRequest
from .base import AIServiceBase
from .cache import SummaryCache

logger = logging.getLogger(__name__)


# Rate limits (can be moved to settings)
PROJECT_SUMMARY_RATE_LIMIT_MINUTES = getattr(
    settings, "PROJECT_SUMMARY_RATE_LIMIT_MINUTES", 5
)
SUMMARY_GLOBAL_LIMIT_PER_HOUR = getattr(settings, "SUMMARY_GLOBAL_LIMIT_PER_HOUR", 100)


class ProjectSummarizer(AIServiceBase):
    """Service for summarizing projects."""

    def __init__(self, provider_handle: str = None):
        """Initialize project summarizer with provider."""
        super().__init__(provider_handle, "AI_PROVIDER")
        self.cache = SummaryCache(
            rate_limit_minutes=PROJECT_SUMMARY_RATE_LIMIT_MINUTES,
            global_limit_per_hour=SUMMARY_GLOBAL_LIMIT_PER_HOUR,
        )

    def project_summarize(
        self,
        project,
        text: str,
        prompt: str | None = None,
        result_type: type[ProjectSummaryResponse] = ProjectSummaryResponse,
        is_rate_limit: bool = True,
        allow_regeneration: bool = True,
    ) -> ProjectSummaryResponse:
        """Summarize project data with caching.

        - Exact hash match: reuse cached summary and update last_checked_at.
        - Rate limits (if enabled): optionally reuse latest summary without touching last_checked_at.
        - If allow_regeneration is False and a summary exists, always return the latest summary
          without generating a new one, even when the hash changed.
        """
        request = SummaryRequest(text=text, prompt=prompt)
        latest = self.cache.get_latest(project)
        text_hash = ProjectSummary.compute_hash(text)

        cached = self.cache.get_cached_response(
            project=project,
            text_hash=text_hash,
            latest=latest,
            is_rate_limit=is_rate_limit,
        )
        if cached:
            return cached

        # No cache hit:
        # - If regeneration is not allowed and we already have a summary,
        #   return the latest one unchanged (used by the button endpoint).
        if not allow_regeneration and latest:
            logger.debug(
                "Regeneration disabled and no cache hit; returning latest summary "
                f"for project {project.id}"
            )
            return ProjectSummaryResponse(**latest.response_data)

        # If there is no existing summary, we must generate one at least once.
        logger.info(f"Generating summary for project {project.id} ({project.slug})")

        try:
            response = self.provider.request(request, result_type=result_type)
            self.cache.save(project, request.prompt_text, text_hash, response)
            return response
        except Exception as e:
            logger.error(f"Summary generation failed: {e}", exc_info=True)
            capture_exception(e)
            raise
