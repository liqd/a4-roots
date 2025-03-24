from django.db import models
from django.core.exceptions import ValidationError
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page
from wagtail.search import index
from wagtail.snippets.models import register_snippet
from django.utils.text import slugify
from django.urls import reverse

from .blocks import LearningContentBlock

@register_snippet
class LearningCategory(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
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
        FieldPanel("slug"),
        FieldPanel("permission_level"),
        FieldPanel("order"),
    ]

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Learning Category"
        verbose_name_plural = "Learning Categories"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            unique_slug = base_slug
            counter = 1

            while LearningCategory.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = unique_slug  
            
        super().save(*args, **kwargs)


    def __str__(self):
        return self.name


class LearningCenterPage(Page):
    """
    Singleton page model for the Learning Center.
    Will contain all learning nuggets organized by category.
    """
    max_count = 1  # Ensures only one instance can be created

    content_panels = Page.content_panels

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["categories"] = LearningCategory.objects.all()
        return context

    parent_page_types = ["a4_candy_cms_pages.HomePage"]
    subpage_types = ["LearningNuggetPage"]

    class Meta:
        verbose_name = "Learning Center Page"

def validate_single_instance(value):
    """Ensures only one item exists in the StreamField."""
    if len(value) > 1:
        raise ValidationError("Only one Learning Nugget is allowed in this field.")
    
class LearningNuggetPage(Page):
    category = models.ForeignKey(
        LearningCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nuggets",
    )

    content = StreamField(
        [("learning_nugget", LearningContentBlock())], 
        use_json_field=True, 
        blank=True,
        validators=[validate_single_instance],
    )

    search_fields = Page.search_fields + [
        index.SearchField("content"),
    ]

    content_panels = Page.content_panels + [
        FieldPanel("category"),
        FieldPanel("content"),
    ]

    parent_page_types = ["LearningCenterPage"]
    subpage_types = []

    def get_absolute_url(self):
        if self.category:
            return reverse("learning_nuggets:nugget", kwargs={
                "category_slug": self.category.slug,
                "nugget_slug": self.slug
            })
        return "#"  # Fallback if no category

    class Meta:
        verbose_name = "Learning Nugget Page"
