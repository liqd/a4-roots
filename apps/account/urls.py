from django.urls import path, include

from . import views

urlpatterns = [
    path("", views.AccountView.as_view(), name="account"),
    path("profile/", views.ProfileUpdateView.as_view(), name="account_profile"),
    path(
        "account_deletion/",
        views.AccountDeletionView.as_view(),
        name="account_deletion",
    ),
    path(
        "agreements/",
        views.OrganisationTermsOfUseUpdateView.as_view(),
        name="user_agreements",
    ),
    path("guest/", include([
        path("convert/", views.GuestConvertView.as_view(), name="guest_convert"),
        path("account_deletion/", views.AccountDeletionView.as_view(), name="guest_account_deletion"),
        path(
            "agreements/",
            views.OrganisationTermsOfUseUpdateView.as_view(),
            name="guest_user_agreements",
        ),
    ])),
]