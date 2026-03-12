"""Caching logic for project summaries."""

import json
import logging
from datetime import timedelta

from django.utils import timezone
from pydantic import BaseModel

from ..models import ProjectSummary
from ..pydantic_models import ProjectSummaryResponse

logger = logging.getLogger(__name__)


class SummaryCache:
    """Handles caching of project summaries."""

    def __init__(self, rate_limit_minutes: int, global_limit_per_hour: int):
        self.rate_limit_minutes = rate_limit_minutes
        self.global_limit_per_hour = global_limit_per_hour

    def get_latest(self, project):
        """Get most recent summary for project."""
        return (
            ProjectSummary.objects.filter(project=project)
            .order_by("-created_at")
            .first()
        )

    def get_cached_response(
        self,
        project,
        text_hash: str,
        latest,
        is_rate_limit: bool,
    ) -> ProjectSummaryResponse | None:
        """Return cached response if valid.

        - Exact hash match: always used, updates last_checked_at.
        - Rate limits: optionally reuse latest summary without touching last_checked_at.
        """
        if not latest:
            return None

        # Exact match of input hash: content is up to date.
        if latest.input_text_hash == text_hash:
            logger.debug(f"Cache hit (exact match) for project {project.id}")
            latest.last_checked_at = timezone.now()
            latest.save(update_fields=["last_checked_at"])
            return ProjectSummaryResponse(**latest.response_data)

        if not is_rate_limit:
            return None

        # Rate limit checks (reuse latest summary without updating last_checked_at)
        age = timezone.now() - latest.created_at

        if age < timedelta(minutes=self.rate_limit_minutes):
            logger.debug(f"Using rate-limited cache for project {project.id}")
            return ProjectSummaryResponse(**latest.response_data)

        if age < timedelta(hours=1):
            recent = ProjectSummary.objects.filter(
                created_at__gte=timezone.now() - timedelta(hours=1)
            ).count()
            if recent >= self.global_limit_per_hour:
                logger.debug(
                    f"Global rate limit reached, using cache for project {project.id}"
                )
                return ProjectSummaryResponse(**latest.response_data)

        return None

    def save(
        self,
        project,
        prompt: str,
        text_hash: str,
        response: BaseModel,
    ):
        """Save successful response to cache."""
        if isinstance(response, ProjectSummaryResponse):
            ProjectSummary.objects.create(
                project=project,
                prompt=prompt,
                input_text_hash=text_hash,
                response_data=json.loads(response.model_dump_json()),
                last_checked_at=timezone.now(),
            )
            logger.info(f"Cached summary for project {project.id}")
