"""Tests for fallback cache behaviour in project_summarize."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.utils import timezone

from adhocracy4.projects.models import Project

from apps.summarization.models import ProjectSummary
from apps.summarization.pydantic_models import ProjectSummaryResponse, Stats
from apps.summarization.services import AIService


@pytest.mark.django_db
@override_settings(PROJECT_SUMMARY_FALLBACK_MAX_AGE_MINUTES=60)
def test_project_summarize_uses_fallback_cache_on_error_when_within_max_age(
    project_factory,
):
    """
    If the provider errors and a fresh ProjectSummary exists (younger than
    PROJECT_SUMMARY_FALLBACK_MAX_AGE_MINUTES), project_summarize should return
    that cached summary instead of raising.
    """
    project: Project = project_factory()
    created_at = timezone.now() - timedelta(minutes=10)

    fallback_data = {
        "title": "Fallback Summary",
        "stats": {"participants": 1, "contributions": 2, "modules": 3},
        "general_summary": "cached summary",
        "general_goals": ["goal"],
        "past_modules": [],
        "current_modules": [],
        "upcoming_modules": [],
    }

    latest = ProjectSummary.objects.create(
        project=project,
        prompt="test-prompt",
        input_text_hash="dummy-hash",
        response_data=fallback_data,
        created_at=created_at,
    )
    assert latest is not None

    service = AIService()

    # Force the provider to fail so that project_summarize must use the fallback.
    with patch.object(service.provider, "request", side_effect=RuntimeError("API down")):
        response = service.project_summarize(
            project=project,
            text="dummy-input",
            prompt=None,
            result_type=ProjectSummaryResponse,
            # Rate-limit-Cache explizit überspringen, wir wollen den Error-/Fallback-Pfad testen.
            is_rate_limit=False,
        )

    assert isinstance(response, ProjectSummaryResponse)
    assert response.general_summary == "cached summary"
    assert response.stats == Stats(participants=1, contributions=2, modules=3)

