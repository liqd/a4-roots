"""Shared utilities for the projects app."""

import json
import logging

from sentry_sdk import capture_exception

from apps.contrib.models import Settings
from apps.summarization.export_utils.attachments.handlers import (
    collect_document_attachments,
)
from apps.summarization.export_utils.attachments.handlers import (
    integrate_document_summaries,
)
from apps.summarization.export_utils.core import generate_full_export
from apps.summarization.pydantic_models import ProjectSummaryResponse
from apps.summarization.services import AIService

logger = logging.getLogger(__name__)


def generate_project_summary(
    project, request=None, base_url=None, *, allow_regeneration=True
):
    """
    Generate AI summary for a project. Used by the view and by the periodic Celery task.

    Args:
        project: Project instance.
        request: Optional Django request (for document absolute URLs). If None, base_url is used.
        base_url: Optional base URL (e.g. settings.WAGTAILADMIN_BASE_URL) when request is None.

    Returns:
        ProjectSummaryResponse from the AI service.

    Raises:
        Exception: Re-raises any exception from the AI service (caller handles display/retry).
    """
    export_data = generate_full_export(project)

    if request is not None or base_url:
        documents_dict, handle_to_source = collect_document_attachments(
            export_data, request=request, base_url=base_url
        )
        if documents_dict:
            try:
                service = AIService()
                document_response = service.request_vision_dict(
                    documents_dict=documents_dict
                )
                integrate_document_summaries(
                    export_data,
                    document_response.documents,
                    handle_to_source,
                )
            except Exception as e:
                logger.error(
                    "Failed to summarize documents for project %s: %s",
                    project.slug,
                    e,
                    exc_info=True,
                )
                capture_exception(e)

    json_text = json.dumps(export_data, indent=2)
    prompt = Settings.get_value("project_summary_prompt")
    service = AIService()
    response = service.project_summarize(
        project=project,
        text=json_text,
        result_type=ProjectSummaryResponse,
        prompt=prompt,
        allow_regeneration=allow_regeneration,
    )
    return response
