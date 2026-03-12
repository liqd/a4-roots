from apps.debate.models import Subject

from ..processing.extractors import extract_comments
from ..processing.module_utils import get_module_status


def export_debates_full(project):
    """Export all debate subjects with comments"""

    debates_data = []
    subjects = Subject.objects.filter(module__project=project)

    for subject in subjects:
        # Get comments for this subject
        comments_list = extract_comments(subject.comments.all())

        debates_data.append(
            {
                "id": subject.id,
                "name": subject.name,
                "description": subject.description,
                "created": subject.created.isoformat(),
                "reference_number": subject.reference_number,
                "slug": subject.slug,
                "active_status": get_module_status(subject.module),
                "module_start": str(subject.module.module_start),
                "module_end": str(subject.module.module_end),
                "module_id": subject.module.id,
                "module_name": subject.module.name,
                "comment_count": subject.comments.count(),
                "comments": comments_list,
                "comment_creator_count": subject.comment_creator_count,
            }
        )

    return debates_data
