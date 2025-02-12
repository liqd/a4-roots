import pytest
from django.conf import settings
from django.test import override_settings
from django.urls import reverse

from apps.users.models import User
from tests.helpers import GuestUserCreator
from tests.helpers import get_emails_for_address


@pytest.mark.django_db
def test_signup_user_newsletter_checked(client):
    resp = client.post(
        reverse("account_signup"),
        {
            "username": "dauser",
            "email": "mail@example.com",
            "get_newsletters": "on",
            "password1": "password",
            "password2": "password",
            "terms_of_use": "on",
            "captcha": "testpass:0",
        },
    )
    assert resp.status_code == 302
    user = User.objects.get()
    assert user.get_newsletters


@pytest.mark.django_db
def test_signup_user_newsletter_not_checked(client):
    resp = client.post(
        reverse("account_signup"),
        {
            "username": "dauser",
            "email": "mail@example.com",
            "password1": "password",
            "password2": "password",
            "terms_of_use": "on",
            "captcha": "testpass:0",
        },
    )
    assert resp.status_code == 302
    user = User.objects.get()
    assert not user.get_newsletters


@pytest.mark.django_db
def test_signup_user_unchecked_terms_of_use(client):
    resp = client.post(
        reverse("account_signup"),
        {
            "username": "dauser",
            "email": "mail@example.com",
            "password1": "password",
            "password2": "password",
            "captcha": "testpass:0",
        },
    )
    assert User.objects.count() == 0
    assert not resp.context["form"].is_valid()
    assert list(resp.context["form"].errors.keys()) == ["terms_of_use"]


@override_settings()
@pytest.mark.django_db
def test_signup_user_without_captcha(client):
    del settings.CAPTCHA_URL
    resp = client.post(
        reverse("account_signup"),
        {
            "username": "dauser",
            "email": "mail@example.com",
            "get_newsletters": "on",
            "password1": "password",
            "password2": "password",
            "terms_of_use": "on",
        },
    )
    assert resp.status_code == 302
    user = User.objects.get()
    assert user.get_newsletters


@override_settings()
@pytest.mark.django_db
def test_signup_user_when_not_captcha(client):
    settings.CAPTCHA_URL = ""
    resp = client.post(
        reverse("account_signup"),
        {
            "username": "dauser",
            "email": "mail@example.com",
            "get_newsletters": "on",
            "password1": "password",
            "password2": "password",
            "terms_of_use": "on",
        },
    )
    assert resp.status_code == 302
    user = User.objects.get()
    assert user.get_newsletters


@override_settings()
@pytest.mark.django_db
def test_convert_guest_user(client):
    guest_user_creator = GuestUserCreator()
    guest_user = guest_user_creator.create_guest_user()
    client.force_login(guest_user)
    guest_email = "mail@example.com"

    response = client.post(
        reverse("guest_convert"),
        data={
            "username": "aguestuser",
            "email": guest_email,
            "password1": "password",
            "password2": "password",
            "terms_of_use": "on",
        },
    )

    assert response.status_code == 302

    user_emails = get_emails_for_address(guest_email)
    assert len(user_emails) == 1
    assert user_emails[0].subject.startswith("Please confirm your registration on")
