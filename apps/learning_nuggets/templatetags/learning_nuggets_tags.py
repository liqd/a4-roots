from django import template

register = template.Library()


@register.simple_tag
def get_permission(permission_level):
    permissions = {
        "participant": "a4_candy_learning_nuggets.view_participant_content",
        "initiator": "a4_candy_learning_nuggets.view_initiator_content",
        "moderator": "a4_candy_learning_nuggets.view_moderator_content",
    }
    return permissions.get(permission_level, "")
