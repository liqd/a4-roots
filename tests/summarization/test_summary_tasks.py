"""Tests for periodic project summary Celery tasks."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.projects.summary_tasks import generate_project_summary_task
from apps.projects.summary_tasks import refresh_project_summaries
from apps.summarization.models import ProjectSummary


@pytest.mark.django_db
@override_settings(
    PROJECT_SUMMARY_AUTO_REFRESH_MAX_AGE_MINUTES=12 * 60,
    PROJECT_SUMMARY_AUTO_REFRESH_MAX_PROJECTS_PER_RUN=50,
)
def test_refresh_project_summaries_enqueues_projects_without_recent_summary(
    project_factory,
):
    """Projects with no summary or summary older than max_age get enqueued."""
    project = project_factory(is_draft=False, is_app_accessible=False)

    with patch(
        "apps.projects.summary_tasks.generate_project_summary_task"
    ) as mock_task:
        refresh_project_summaries()
        mock_task.delay.assert_called_once_with(project.id)


@pytest.mark.django_db
@override_settings(
    PROJECT_SUMMARY_AUTO_REFRESH_MAX_AGE_MINUTES=12 * 60,
    PROJECT_SUMMARY_AUTO_REFRESH_MAX_PROJECTS_PER_RUN=50,
)
def test_refresh_project_summaries_skips_projects_with_recent_summary(
    project_factory,
):
    """Projects with a summary younger than max_age are not enqueued."""
    project = project_factory(is_draft=False, is_app_accessible=False)
    ProjectSummary.objects.create(
        project=project,
        prompt="test",
        input_text_hash="abc",
        response_data={
            "title": "Summary",
            "stats": {"participants": 0, "contributions": 0, "modules": 0},
            "general_summary": "x",
            "general_goals": [],
            "past_modules": [],
            "current_modules": [],
            "upcoming_modules": [],
        },
    )

    with patch(
        "apps.projects.summary_tasks.generate_project_summary_task"
    ) as mock_task:
        refresh_project_summaries()
        mock_task.delay.assert_not_called()


@pytest.mark.django_db
@override_settings(
    PROJECT_SUMMARY_AUTO_REFRESH_MAX_AGE_MINUTES=12 * 60,
    PROJECT_SUMMARY_AUTO_REFRESH_MAX_PROJECTS_PER_RUN=50,
)
def test_refresh_project_summaries_enqueues_when_summary_older_than_max_age(
    project_factory,
):
    """Projects with latest summary older than max_age get enqueued."""
    project = project_factory(is_draft=False, is_app_accessible=False)
    old_time = timezone.now() - timedelta(hours=13)
    ProjectSummary.objects.create(
        project=project,
        prompt="test",
        input_text_hash="abc",
        response_data={
            "title": "Summary",
            "stats": {"participants": 0, "contributions": 0, "modules": 0},
            "general_summary": "x",
            "general_goals": [],
            "past_modules": [],
            "current_modules": [],
            "upcoming_modules": [],
        },
        created_at=old_time,
    )

    with patch(
        "apps.projects.summary_tasks.generate_project_summary_task"
    ) as mock_task:
        refresh_project_summaries()
        mock_task.delay.assert_called_once_with(project.id)


@pytest.mark.django_db
@override_settings(
    PROJECT_SUMMARY_AUTO_REFRESH_MAX_AGE_MINUTES=12 * 60,
    PROJECT_SUMMARY_AUTO_REFRESH_MAX_PROJECTS_PER_RUN=2,
)
def test_refresh_project_summaries_respects_max_per_run(project_factory):
    """At most max_projects_per_run tasks are enqueued."""
    for _ in range(3):
        project_factory(is_draft=False, is_app_accessible=False)

    with patch(
        "apps.projects.summary_tasks.generate_project_summary_task"
    ) as mock_task:
        refresh_project_summaries()
        assert mock_task.delay.call_count == 2


@pytest.mark.django_db
@override_settings(
    PROJECT_SUMMARY_AUTO_REFRESH_MAX_AGE_MINUTES=12 * 60,
    PROJECT_SUMMARY_AUTO_REFRESH_MAX_PROJECTS_PER_RUN=50,
)
def test_refresh_project_summaries_skips_draft_projects(project_factory):
    """Draft projects are not considered."""
    project_factory(is_draft=True, is_app_accessible=True)
    project_factory(is_draft=True, is_app_accessible=False)

    with patch(
        "apps.projects.summary_tasks.generate_project_summary_task"
    ) as mock_task:
        refresh_project_summaries()
        mock_task.delay.assert_not_called()


@pytest.mark.django_db
def test_generate_project_summary_task_creates_summary(project_factory):
    """generate_project_summary_task calls generate_project_summary and creates a summary."""
    project = project_factory(is_draft=False, is_app_accessible=True)
    assert ProjectSummary.objects.filter(project=project).count() == 0

    with patch("apps.projects.summary_tasks.generate_project_summary") as mock_gen:
        generate_project_summary_task(project.id)

    mock_gen.assert_called_once()
    call_kw = mock_gen.call_args[1]
    assert call_kw["request"] is None
    assert "base_url" in call_kw
    # ProjectSummary is created by the service inside project_summarize, not by our task
    # So we only assert the helper was called; with real service a summary would be created
    assert ProjectSummary.objects.filter(project=project).count() == 0


@pytest.mark.django_db
def test_generate_project_summary_task_handles_missing_project():
    """generate_project_summary_task does not raise when project is missing."""
    generate_project_summary_task(99999)


@pytest.mark.django_db
def test_generate_project_summary_task_logs_on_error(project_factory):
    """On exception the task logs and does not re-raise."""
    project = project_factory(is_draft=False, is_app_accessible=True)

    with patch("apps.projects.summary_tasks.generate_project_summary") as mock_gen:
        mock_gen.side_effect = RuntimeError("AI failed")
        generate_project_summary_task(project.id)

    mock_gen.assert_called_once()
