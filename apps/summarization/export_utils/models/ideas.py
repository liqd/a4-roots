from apps.ideas.models import Idea

from ..processing.extractors import extract_attachments
from ..processing.extractors import extract_comments
from ..processing.extractors import extract_ratings
from ..processing.module_utils import get_module_status


def export_ideas_full(project):
    """Export all ideas with full data"""
    ideas_data = []
    ideas = (
        Idea.objects.filter(module__project=project)
        .select_related("category")
        .prefetch_related("labels")
    )

    for idea in ideas:
        # Get comments for this idea
        comments_list = extract_comments(idea.comments.all())

        # Get ratings for this idea
        ratings_list = extract_ratings(idea.ratings.all())

        ideas_data.append(
            {
                "id": idea.id,
                "active_status": get_module_status(idea.module),
                "module_start": str(idea.module.module_start),
                "module_end": str(idea.module.module_end),
                "url": idea.get_absolute_url(),
                "name": idea.name,
                "description": str(idea.description),
                "attachments": extract_attachments(str(idea.description)),
                "created": idea.created.isoformat(),
                "reference_number": idea.reference_number,
                "category": idea.category.name if idea.category else None,
                "labels": [label.name for label in idea.labels.all()],
                "comment_count": idea.comments.count(),
                "comments": comments_list,
                "rating_count": idea.ratings.count(),
                "ratings": ratings_list,
                "module_id": idea.module.id,
                "module_name": idea.module.name,
                "images": [i.name for i in idea._a4images_current_images],
            }
        )

    return ideas_data
