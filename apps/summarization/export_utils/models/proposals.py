from apps.budgeting.models import Proposal

from ..processing.extractors import extract_attachments
from ..processing.extractors import extract_comments
from ..processing.extractors import extract_ratings
from ..processing.module_utils import get_module_status


def export_proposals_full(project):
    """Export all participatory budgeting proposals with full data including budget."""

    proposals_data = []
    proposals = (
        Proposal.objects.filter(module__project=project)
        .select_related("category")
        .prefetch_related("labels")
    )

    for proposal in proposals:
        # Get comments for this proposal
        comments_list = extract_comments(proposal.comments.all())

        # Get ratings for this proposal
        ratings_list = extract_ratings(proposal.ratings.all())

        # Extract point coordinates if they exist
        point_data = None
        if proposal.point:
            if hasattr(proposal.point, "y"):
                point_data = {
                    "latitude": proposal.point.y,
                    "longitude": proposal.point.x,
                    "srid": proposal.point.srid,
                }
            elif isinstance(proposal.point, dict):
                point_data = proposal.point

        proposals_data.append(
            {
                "id": proposal.id,
                "active_status": get_module_status(proposal.module),
                "module_start": str(proposal.module.module_start),
                "module_end": str(proposal.module.module_end),
                "url": proposal.get_absolute_url(),
                "name": proposal.name,
                "description": str(proposal.description),
                "attachments": extract_attachments(str(proposal.description)),
                "budget": proposal.budget,
                "point": point_data,
                "point_label": proposal.point_label,
                "created": proposal.created.isoformat(),
                "reference_number": proposal.reference_number,
                "category": proposal.category.name if proposal.category else None,
                "labels": [label.name for label in proposal.labels.all()],
                "comment_count": proposal.comments.count(),
                "comments": comments_list,
                "rating_count": proposal.ratings.count(),
                "ratings": ratings_list,
                "module_id": proposal.module.id,
                "module_name": proposal.module.name,
                "images": [i.name for i in proposal._a4images_current_images],
                "is_archived": proposal.is_archived,
            }
        )

    return proposals_data
