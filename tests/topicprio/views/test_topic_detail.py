import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from guest_user.functions import is_guest_user

from adhocracy4.projects.enums import Access
from adhocracy4.test.helpers import assert_template_response
from adhocracy4.test.helpers import freeze_phase
from adhocracy4.test.helpers import redirect_target
from adhocracy4.test.helpers import setup_phase
from apps.topicprio import phases
from tests.helpers import GuestUserCreator


@pytest.mark.django_db
def test_detail_view(client, phase_factory, topic_factory):
    phase, module, project, topic = setup_phase(
        phase_factory, topic_factory, phases.PrioritizePhase
    )
    url = topic.get_absolute_url()
    with freeze_phase(phase):
        response = client.get(url)
        assert_template_response(response, "a4_candy_topicprio/topic_detail.html")
        assert response.status_code == 200


@pytest.mark.django_db
def test_detail_view_private_not_visible_anonymous(
    client, phase_factory, topic_factory
):
    phase, module, project, topic = setup_phase(
        phase_factory, topic_factory, phases.PrioritizePhase
    )
    topic.module.project.access = Access.PRIVATE
    topic.module.project.save()
    url = topic.get_absolute_url()
    response = client.get(url)
    assert response.status_code == 302
    assert redirect_target(response) == "account_login"


@pytest.mark.django_db
def test_detail_view_private_not_visible_normal_user(
    client, user, phase_factory, topic_factory
):
    phase, module, project, topic = setup_phase(
        phase_factory, topic_factory, phases.PrioritizePhase
    )
    topic.module.project.access = Access.PRIVATE
    topic.module.project.save()
    assert user not in topic.module.project.participants.all()
    client.login(username=user.email, password="password")
    url = topic.get_absolute_url()
    response = client.get(url)
    assert response.status_code == 403


@pytest.mark.django_db
def test_detail_view_private_not_visible_guest_user(
    client, user, phase_factory, topic_factory
):
    phase, module, project, topic = setup_phase(
        phase_factory, topic_factory, phases.PrioritizePhase
    )
    topic.module.project.access = Access.PRIVATE
    topic.module.project.save()

    guest_user_creator = GuestUserCreator()
    guest_user = guest_user_creator.create_guest_user()
    assert is_guest_user(guest_user)

    assert user not in topic.module.project.participants.all()
    client.force_login(guest_user)
    url = topic.get_absolute_url()
    response = client.get(url)
    assert response.status_code == 403


@pytest.mark.django_db
def test_detail_view_private_visible_to_participant(
    client, user, phase_factory, topic_factory
):
    phase, module, project, topic = setup_phase(
        phase_factory, topic_factory, phases.PrioritizePhase
    )
    topic.module.project.access = Access.PRIVATE
    topic.module.project.save()
    url = topic.get_absolute_url()
    assert user not in topic.module.project.participants.all()
    topic.module.project.participants.add(user)
    client.login(username=user.email, password="password")
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_detail_view_private_visible_to_moderator(client, phase_factory, topic_factory):
    phase, module, project, topic = setup_phase(
        phase_factory, topic_factory, phases.PrioritizePhase
    )
    topic.module.project.access = Access.PRIVATE
    topic.module.project.save()
    url = topic.get_absolute_url()
    user = topic.project.moderators.first()
    client.login(username=user.email, password="password")
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_detail_view_private_visible_to_initiator(client, phase_factory, topic_factory):
    phase, module, project, topic = setup_phase(
        phase_factory, topic_factory, phases.PrioritizePhase
    )
    topic.module.project.access = Access.PRIVATE
    topic.module.project.save()
    url = topic.get_absolute_url()
    user = topic.project.organisation.initiators.first()
    client.login(username=user.email, password="password")
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_detail_view_semipublic_participation_only_participant(
    client, user, phase_factory, topic_factory
):
    phase, module, project, topic = setup_phase(
        phase_factory, topic_factory, phases.PrioritizePhase
    )
    topic.module.project.access = Access.SEMIPUBLIC
    topic.module.project.save()

    url = topic.get_absolute_url()
    topic_ct = ContentType.objects.get_for_model(type(topic))
    api_url = reverse(
        "comments-list", kwargs={"content_type": topic_ct.pk, "object_pk": topic.pk}
    )
    comment_data = {"comment": "no comment", "agreed_terms_of_use": True}

    with freeze_phase(phase):
        response = client.get(url)
        assert response.status_code == 200
        assert_template_response(response, "a4_candy_topicprio/topic_detail.html")
        response = client.post(api_url, comment_data, format="json")

        assert response.status_code == 403

        client.login(username=user.email, password="password")

        response = client.get(url)
        assert response.status_code == 200
        assert_template_response(response, "a4_candy_topicprio/topic_detail.html")
        response = client.post(api_url, comment_data, format="json")
        assert response.status_code == 403

        topic.module.project.participants.add(user)

        response = client.get(url)
        assert response.status_code == 200
        assert_template_response(response, "a4_candy_topicprio/topic_detail.html")
        response = client.post(api_url, comment_data, format="json")
        assert response.status_code == 201


@pytest.mark.django_db
def test_detail_view_public_visible_guest_user(
    client, user, phase_factory, topic_factory
):
    phase, module, project, topic = setup_phase(
        phase_factory, topic_factory, phases.PrioritizePhase
    )

    guest_user_creator = GuestUserCreator()
    guest_user = guest_user_creator.create_guest_user()
    assert is_guest_user(guest_user)

    assert user not in topic.module.project.participants.all()
    client.force_login(guest_user)

    url = topic.get_absolute_url()
    with freeze_phase(phase):
        response = client.get(url)
        assert_template_response(response, "a4_candy_topicprio/topic_detail.html")
        assert response.status_code == 200
