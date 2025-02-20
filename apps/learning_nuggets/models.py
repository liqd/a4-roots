from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page
from wagtail.search import index
from wagtail.snippets.models import register_snippet

from .blocks import LearningContentBlock


@register_snippet
class LearningCategory(models.Model):
    name = models.CharField(max_length=255)
    permission_level = models.CharField(
        max_length=50,
        choices=[
            ("participant", "Participant"),
            ("initiator", "Initiator"),
            ("moderator", "Moderator"),
        ],
        default="participant",
    )
    order = models.IntegerField(default=0)

    panels = [
        FieldPanel("name"),
        FieldPanel("permission_level"),
        FieldPanel("order"),
    ]

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Learning Category"
        verbose_name_plural = "Learning Categories"

    def __str__(self):
        return self.name


class LearnCenterPage(Page):
    """
    Singleton page model for the Learn Center.
    Will contain all learning nuggets organized by category.
    """

    max_count = 1  # Ensures only one instance can be created

    content_panels = Page.content_panels

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["categories"] = LearningCategory.objects.all()
        return context

    parent_page_types = ["wagtailcore.Page"]
    subpage_types = ["LearningNuggetPage"]

    class Meta:
        verbose_name = "Learn Center"


class LearningNuggetPage(Page):
    category = models.ForeignKey(
        LearningCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nuggets",
    )
    content = StreamField(
        [("learning_nugget", LearningContentBlock())], use_json_field=True, blank=True
    )

    search_fields = Page.search_fields + [
        index.SearchField("content"),
    ]

    content_panels = Page.content_panels + [
        FieldPanel("category"),
        FieldPanel("content"),
    ]

    parent_page_types = ["LearnCenterPage"]
    subpage_types = []

    def get_absolute_url(self):
        return f"/help/nugget/{self.slug}/"

    class Meta:
        verbose_name = "Learning Nugget"
