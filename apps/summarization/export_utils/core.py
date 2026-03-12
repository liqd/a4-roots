from .models.debates import export_debates_full
from .models.documents import export_documents_full
from .models.ideas import export_ideas_full
from .models.mapideas import export_mapideas_full
from .models.offline_events import export_offline_events_full
from .models.polls import export_polls_full
from .models.proposals import export_proposals_full
from .models.topics import export_topics_full
from .processing.extractors import extract_attachments
from .processing.grouping import group_by_module


def generate_full_export(project):
    """Generate complete project export data"""
    description_attachments = extract_attachments(project.description)
    information_attachments = (
        extract_attachments(project.information)
        if hasattr(project, "information")
        else []
    )
    result_attachments = extract_attachments(project.result)

    export = {
        "project": {
            "name": project.name,
            "description": project.description,
            "description_attachments": description_attachments,
            "information": (
                project.information if hasattr(project, "information") else None
            ),
            "information_attachments": information_attachments,
            "slug": project.slug,
            "organisation": project.organisation.name,
            "result": project.result,
            "result_attachments": result_attachments,
            "url": project.get_absolute_url(),
        },
        "ideas": export_ideas_full(project),
        "polls": export_polls_full(project),
        "mapideas": export_mapideas_full(project),
        "proposals": export_proposals_full(project),
        "topics": export_topics_full(project),
        "debates": export_debates_full(project),
        "documents": export_documents_full(project),
        "offline_events": export_offline_events_full(project),
    }
    structured = group_by_module(export)
    # print(json.dumps(structured))
    return structured
