"""Project summarization service."""

import json
import logging
from typing import Any
from typing import Dict
from typing import List

from django.conf import settings
from sentry_sdk import capture_exception

from ..models import ProjectSummary
from ..pydantic_models import GeneralInfo
from ..pydantic_models import GeneralInfoResponse
from ..pydantic_models import ModuleDebug
from ..pydantic_models import ModuleFinal
from ..pydantic_models import ModuleSummaryResponse
from ..pydantic_models import PhaseModule
from ..pydantic_models import Phases
from ..pydantic_models import PhaseSection
from ..pydantic_models import ProjectSummaryResponse
from ..requests.project import GeneralInfoRequest
from ..requests.project import ModuleSummaryRequest
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
    """Service for summarizing projects module by module."""

    def __init__(self, provider_handle: str = None):
        """Initialize project summarizer with provider."""
        super().__init__(provider_handle, "AI_PROVIDER")
        self.cache = SummaryCache(
            rate_limit_minutes=PROJECT_SUMMARY_RATE_LIMIT_MINUTES,
            global_limit_per_hour=SUMMARY_GLOBAL_LIMIT_PER_HOUR,
        )

    def _process_module(self, module: Dict[str, Any], phase: str) -> PhaseModule:
        """Process a single module and return its summary."""
        try:
            request = ModuleSummaryRequest(module, phase)
            response = self.provider.request(request, result_type=ModuleSummaryResponse)

            # Create debug info if present in module data
            debug = None
            if "debug" in module:
                debug = ModuleDebug(**module["debug"])

            return PhaseModule(
                module_id=module.get("module_id"),
                module_name=module.get("module_name", "Unknown"),
                status=phase,  # 'past', 'current', 'upcoming'
                debug=debug,
                final=ModuleFinal(summary=response.summary, bullets=response.bullets),
            )

        except Exception as e:
            logger.error(f"Failed to summarize module {module.get('module_id')}: {e}")
            capture_exception(e)

            # Return fallback module
            return PhaseModule(
                module_id=module.get("module_id", 0),
                module_name=module.get("module_name", "Unknown"),
                status=phase,
                debug=None,
                final=ModuleFinal(
                    summary="Summary temporarily unavailable",
                    bullets=["Could not generate summary for this module"],
                ),
            )

    def _process_phase(
        self, phase_data: Dict[str, Any], phase_name: str
    ) -> List[PhaseModule]:
        """Process all modules in a phase."""
        modules = phase_data.get("modules", [])
        return [self._process_module(module, phase_name) for module in modules]

    def project_summarize(
        self,
        project,  # Django project model instance
        text: str,  # JSON string containing project data
        prompt: str | None = None,
        result_type: type[ProjectSummaryResponse] = ProjectSummaryResponse,
        is_rate_limit: bool = True,
        allow_regeneration: bool = True,
    ) -> ProjectSummaryResponse:
        """Summarize project data module by module.

        Args:
            project: Django project model instance (for caching)
            text: JSON string containing the full project export data
            prompt: Optional custom prompt
            result_type: Expected response type
            is_rate_limit: Whether to apply rate limiting
            allow_regeneration: Whether to generate new summary if cache miss
        """
        # Parse the JSON string into a dictionary
        try:
            project_data = json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse project data JSON: {e}")
            # Fall back to legacy method if JSON parsing fails
            return self._legacy_summarize(
                project, text, prompt, result_type, is_rate_limit, allow_regeneration
            )

        # Check cache using the text parameter (string version for hashing)
        text_hash = ProjectSummary.compute_hash(text)
        latest = self.cache.get_latest(project)

        cached = self.cache.get_cached_response(
            project=project,
            text_hash=text_hash,
            latest=latest,
            is_rate_limit=is_rate_limit,
        )
        if cached:
            return cached

        if not allow_regeneration and latest:
            logger.debug(
                f"Regeneration disabled, returning cached summary for project {project.id}"
            )
            return ProjectSummaryResponse(**latest.response_data)

        logger.info(
            f"Generating module-by-module summary for project {project.id} ({project.slug})"
        )

        try:
            # Process each phase
            phases_data = project_data.get("phases", {})

            past_modules = self._process_phase(phases_data.get("past", {}), "past")
            current_modules = self._process_phase(
                phases_data.get("current", {}), "current"
            )
            upcoming_modules = self._process_phase(
                phases_data.get("upcoming", {}), "upcoming"
            )

            all_modules = past_modules + current_modules + upcoming_modules

            # Get general project summary
            general_request = GeneralInfoRequest(
                project_data, [m.dict() for m in all_modules]
            )  # Convert to dict for the request
            general_response = self.provider.request(
                general_request, result_type=GeneralInfoResponse
            )

            # Build complete response
            response = ProjectSummaryResponse(
                title=f"Summary of {project_data.get('project', {}).get('name', 'participation')}",
                general_info=GeneralInfo(
                    summary=general_response.summary, goals=general_response.goals
                ),
                phases=Phases(
                    past=PhaseSection(modules=past_modules),
                    current=PhaseSection(modules=current_modules),
                    upcoming=PhaseSection(modules=upcoming_modules),
                ),
            )

            # Cache the result
            self.cache.save(project, prompt or "module-by-module", text_hash, response)

            return response

        except Exception as e:
            logger.error(f"Summary generation failed: {e}", exc_info=True)
            capture_exception(e)
            raise

    def _legacy_summarize(
        self,
        project,
        text: str,
        prompt: str | None = None,
        result_type: type[ProjectSummaryResponse] = ProjectSummaryResponse,
        is_rate_limit: bool = True,
        allow_regeneration: bool = True,
    ) -> ProjectSummaryResponse:
        """Fallback to original summarization method."""
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

        if not allow_regeneration and latest:
            logger.debug(
                f"Regeneration disabled, returning cached summary for project {project.id}"
            )
            return ProjectSummaryResponse(**latest.response_data)

        logger.info(
            f"Generating legacy summary for project {project.id} ({project.slug})"
        )

        try:
            response = self.provider.request(request, result_type=result_type)
            self.cache.save(project, request.prompt_text, text_hash, response)
            return response
        except Exception as e:
            logger.error(f"Summary generation failed: {e}", exc_info=True)
            capture_exception(e)
            raise
