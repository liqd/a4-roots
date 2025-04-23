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


@register.filter(name="filter_by_block_type")
def filter_by_block_type(blocks, block_type):
    """Filters StreamField blocks by their block_type."""
    return [block for block in blocks if block.block_type == block_type and block.value]
