from django.apps import apps
from django.conf import settings
from django.contrib.auth.decorators import user_passes_test

Category = apps.get_model("your_app", "Category")

def user_is_category_member(view_func):
    """Category member view decorator.

    Checks that the user is a member of any category.
    """
    return user_passes_test(
        _user_is_category_member,
    )(view_func)

def _user_is_category_member(user):
    return (
        user.is_active
        and Category.objects.filter(members__id=user.id).exists()
    )
