"""URL configuration for summarization app."""

from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "summarization"

urlpatterns = [
    path("", RedirectView.as_view(url="test/", permanent=False), name="index"),
    path("test/", views.SummarizationTestView.as_view(), name="test"),
]
