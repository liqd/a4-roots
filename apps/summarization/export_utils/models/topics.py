from apps.topicprio.models import Topic

from ..processing.extractors import extract_comments
from ..processing.extractors import extract_ratings
from ..processing.module_utils import get_module_status


def export_topics_full(project):
    """Export all topics with full data"""

    topics_data = []
    topics = (
        Topic.objects.filter(module__project=project)
        .select_related("category")
        .prefetch_related("labels")
    )

    for topic in topics:
        # Get comments for this topic
        comments_list = extract_comments(topic.comments.all())

        # Get ratings for this topic
        ratings_list = extract_ratings(topic.ratings.all())

        topics_data.append(
            {
                "id": topic.id,
                "active_status": get_module_status(topic.module),
                "module_start": str(topic.module.module_start),
                "module_end": str(topic.module.module_end),
                "url": topic.get_absolute_url(),
                "name": topic.name,
                "description": str(topic.description),
                "created": topic.created.isoformat(),
                "reference_number": topic.reference_number,
                "category": topic.category.name if topic.category else None,
                "labels": [label.name for label in topic.labels.all()],
                "comment_count": topic.comments.count(),
                "comments": comments_list,
                "rating_count": topic.ratings.count(),
                "ratings": ratings_list,
                "module_id": topic.module.id,
                "module_name": topic.module.name,
            }
        )

    return topics_data
