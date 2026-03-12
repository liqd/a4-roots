from apps.mapideas.models import MapIdea

from ..processing.extractors import extract_attachments
from ..processing.extractors import extract_comments
from ..processing.extractors import extract_ratings
from ..processing.module_utils import get_module_status


def export_mapideas_full(project):
    """Export all map ideas with full data including point coordinates."""

    mapideas_data = []
    mapideas = (
        MapIdea.objects.filter(module__project=project)
        .select_related("category")
        .prefetch_related("labels")
    )

    for mapidea in mapideas:
        # Get comments for this map idea
        comments_list = extract_comments(mapidea.comments.all())

        # Get ratings for this map idea
        ratings_list = extract_ratings(mapidea.ratings.all())

        # Extract point coordinates if they exist
        point_data = None
        if mapidea.point:
            # Check if it's a dict or geometry object
            if hasattr(mapidea.point, "y"):
                # It's a geometry object
                point_data = {
                    "latitude": mapidea.point.y,
                    "longitude": mapidea.point.x,
                    "srid": mapidea.point.srid,
                }
            elif isinstance(mapidea.point, dict):
                # It's already a dict
                point_data = mapidea.point
            else:
                # Try to convert to dict
                point_data = {
                    "latitude": getattr(mapidea.point, "y", None),
                    "longitude": getattr(mapidea.point, "x", None),
                }

        mapideas_data.append(
            {
                "id": mapidea.id,
                "active_status": get_module_status(mapidea.module),
                "module_start": str(mapidea.module.module_start),
                "module_end": str(mapidea.module.module_end),
                "url": mapidea.get_absolute_url(),
                "name": mapidea.name,
                "description": str(mapidea.description),
                "attachments": extract_attachments(str(mapidea.description)),
                "point": point_data,
                "point_label": mapidea.point_label,
                "created": mapidea.created.isoformat(),
                "reference_number": mapidea.reference_number,
                "category": mapidea.category.name if mapidea.category else None,
                "labels": [label.name for label in mapidea.labels.all()],
                "comment_count": mapidea.comments.count(),
                "comments": comments_list,
                "rating_count": mapidea.ratings.count(),
                "ratings": ratings_list,
                "module_id": mapidea.module.id,
                "module_name": mapidea.module.name,
                "images": [i.name for i in mapidea._a4images_current_images],
            }
        )

    return mapideas_data
