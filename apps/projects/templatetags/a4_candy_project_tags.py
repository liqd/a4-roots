from django import template

from adhocracy4.comments.models import Comment
from adhocracy4.polls.models import Vote
from apps.budgeting.models import Proposal as budget_proposal
from apps.ideas.models import Idea
from apps.interactiveevents.models import Like
from apps.interactiveevents.models import LiveQuestion
from apps.mapideas.models import MapIdea

register = template.Library()


@register.filter
def project_url(project):
    return project.get_absolute_url()


@register.simple_tag
def to_class_name(value):
    return value.__class__.__name__


@register.simple_tag
def get_num_entries(module):
    """Count all user-generated items."""
    item_count = (
        Idea.objects.filter(module=module).count()
        + MapIdea.objects.filter(module=module).count()
        + budget_proposal.objects.filter(module=module).count()
        + Comment.objects.filter(idea__module=module).count()
        + Comment.objects.filter(mapidea__module=module).count()
        + Comment.objects.filter(budget_proposal__module=module).count()
        + Comment.objects.filter(paragraph__chapter__module=module).count()
        + Comment.objects.filter(chapter__module=module).count()
        + Comment.objects.filter(poll__module=module).count()
        + Comment.objects.filter(topic__module=module).count()
        + Comment.objects.filter(subject__module=module).count()
        + Vote.objects.filter(choice__question__poll__module=module).count()
        + LiveQuestion.objects.filter(module=module).count()
        + Like.objects.filter(livequestion__module=module).count()
    )

    return item_count


@register.filter
def get_module_by_id(queryset, id):
    """Get a module by ID from a queryset, return None if id is None or invalid"""
    if not id:
        return None
    try:
        return queryset.filter(id=id).first()
    except (ValueError, TypeError):
        return None


@register.filter
def module_image(module_name):
    MODULE_IMAGES = {
        "brainstorming": "images/brainstorming.svg",
        "map-brainstorming": "images/map-brainstorming.svg",
        "idea-collection": "images/agenda-setting.svg",
        "idea-challenge": "images/agenda-setting.svg",
        "map-idea-collection": "images/map-idea-collection.svg",
        "map-idea-challenge": "images/map-idea-collection.svg",
        "text-review": "images/text-review.svg",
        "poll": "images/poll.svg",
        "participatory-budgeting": "images/participatory-budgeting.svg",
        "interactive-event": "images/live-discussion.svg",
        "topic-prioritization": "images/priorization.svg",
        "prioritization": "images/priorization.svg",
        "debate": "images/debate.svg",
    }
    return MODULE_IMAGES.get(module_name.lower(), "images/default.svg")
