from apps.documents.models import Chapter

from ..processing.extractors import extract_attachments
from ..processing.extractors import extract_comments
from ..processing.module_utils import get_module_status


def export_documents_full(project):
    """Export all document chapters and paragraphs with comments"""

    documents_data = []
    chapters = Chapter.objects.filter(module__project=project)

    for chapter in chapters:
        # Get chapter comments
        chapter_comments = extract_comments(chapter.comments.all())

        # Get paragraphs for this chapter
        paragraphs_list = []
        for paragraph in chapter.paragraphs.all().order_by("weight"):
            # Get paragraph comments
            paragraph_comments = extract_comments(paragraph.comments.all())

            paragraphs_list.append(
                {
                    "id": paragraph.id,
                    "name": paragraph.name,
                    "text": str(paragraph.text),
                    "attachments": extract_attachments(str(paragraph.text)),
                    "weight": paragraph.weight,
                    "created": paragraph.created.isoformat(),
                    "comment_count": paragraph.comments.count(),
                    "comments": paragraph_comments,
                }
            )

        documents_data.append(
            {
                "id": chapter.id,
                "name": chapter.name,
                "url": chapter.get_absolute_url(),
                "weight": chapter.weight,
                "created": chapter.created.isoformat(),
                "active_status": get_module_status(chapter.module),
                "module_start": str(chapter.module.module_start),
                "module_end": str(chapter.module.module_end),
                "module_id": chapter.module.id,
                "module_name": chapter.module.name,
                "prev_chapter_id": chapter.prev.id if chapter.prev else None,
                "next_chapter_id": chapter.next.id if chapter.next else None,
                "paragraph_count": chapter.paragraphs.count(),
                "paragraphs": paragraphs_list,
                "chapter_comment_count": chapter.comments.count(),
                "chapter_comments": chapter_comments,
                "total_paragraph_comments": sum(
                    p["comment_count"] for p in paragraphs_list
                ),
            }
        )

    return documents_data
