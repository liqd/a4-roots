import pytest
from django.urls import reverse

from apps.summarization.models import ProjectSummary
from apps.summarization.models import SummaryFeedback


def _create_summary(project):
    return ProjectSummary.objects.create(
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


@pytest.mark.django_db
def test_summary_feedback_invalid_request_returns_400(client, project_factory):
    project = project_factory()
    summary = _create_summary(project)

    url = reverse(
        "project-summary-feedback",
        kwargs={
            "organisation_slug": project.organisation.slug,
            "slug": project.slug,
        },
    )

    # invalid feedback value
    response = client.post(
        url,
        {
            "summary_id": str(summary.id),
            "feedback": "invalid",
        },
    )
    assert response.status_code == 400

    # missing summary_id
    response = client.post(
        url,
        {
            "feedback": "positive",
        },
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_summary_feedback_toggle_for_authenticated_user(client, project_factory, user):
    project = project_factory()
    summary = _create_summary(project)

    url = reverse(
        "project-summary-feedback",
        kwargs={
            "organisation_slug": project.organisation.slug,
            "slug": project.slug,
        },
    )

    client.force_login(user)

    # First click: create positive feedback
    response = client.post(
        url,
        {
            "summary_id": str(summary.id),
            "feedback": "positive",
        },
    )
    assert response.status_code == 200
    fb = SummaryFeedback.objects.get(summary=summary, user=user)
    assert fb.feedback == "positive"

    # Same button again: remove feedback
    response = client.post(
        url,
        {
            "summary_id": str(summary.id),
            "feedback": "positive",
        },
    )
    assert response.status_code == 200
    assert not SummaryFeedback.objects.filter(summary=summary, user=user).exists()

    # Switch to negative: new feedback is stored
    response = client.post(
        url,
        {
            "summary_id": str(summary.id),
            "feedback": "negative",
        },
    )
    assert response.status_code == 200
    fb = SummaryFeedback.objects.get(summary=summary, user=user)
    assert fb.feedback == "negative"


@pytest.mark.django_db
def test_summary_feedback_uses_session_for_anonymous_user(client, project_factory):
    project = project_factory()
    summary = _create_summary(project)

    url = reverse(
        "project-summary-feedback",
        kwargs={
            "organisation_slug": project.organisation.slug,
            "slug": project.slug,
        },
    )

    # First click as anonymous user: feedback is stored with session_key
    response = client.post(
        url,
        {
            "summary_id": str(summary.id),
            "feedback": "positive",
        },
    )
    assert response.status_code == 200

    fb = SummaryFeedback.objects.get(summary=summary)
    assert fb.user is None
    assert fb.session_key

    session_key = fb.session_key

    # Second click on same button: feedback is removed
    response = client.post(
        url,
        {
            "summary_id": str(summary.id),
            "feedback": "positive",
        },
    )
    assert response.status_code == 200
    assert not SummaryFeedback.objects.filter(
        summary=summary, session_key=session_key
    ).exists()
