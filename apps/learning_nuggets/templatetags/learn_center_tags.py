from django import template
from django.core.cache import cache

from ..models import LearningCategory

register = template.Library()


@register.simple_tag
def get_learn_center_content():
    # Cache the result to avoid repeated queries
    cache_key = "learn_center_content"
    content = cache.get(cache_key)

    if content is None:
        categories = LearningCategory.objects.prefetch_related("nuggets").all()

        content = {
            "categories": categories,
        }
        cache.set(cache_key, content, 3600)  # Cache for 1 hour

    return content
