import importlib

from django.conf import settings
from django.core import urlresolvers
from django.utils import six
from django.utils.functional import lazy

django_reverse = None
django_reverse_lazy = None


def patch_reverse():
    """Overwrite the default reverse implementation.

    Monkey-patches the urlresolvers.reverse function. Will not patch twice.
    """
    if hasattr(settings, 'REVERSE_METHOD') and django_reverse is None:
        global django_reverse, django_reverse_lazy
        django_reverse = urlresolvers.reverse
        django_reverse_lazy = urlresolvers.reverse_lazy

        module_name, func_name = settings.REVERSE_METHOD.rsplit('.', 1)
        reverse = getattr(importlib.import_module(module_name), func_name)

        urlresolvers.reverse = reverse
        urlresolvers.reverse_lazy = lazy(reverse, six.text_type)


def reset_reverse():
    """Restore the default reverse implementation."""
    if django_reverse is not None:
        urlresolvers.reverse = django_reverse
        urlresolvers.reverse_lazy = django_reverse_lazy
