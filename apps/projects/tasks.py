import importlib

from celery import shared_task

from .summary_tasks import generate_project_summary_task  # noqa: F401
from .summary_tasks import refresh_project_summaries  # noqa: F401


@shared_task
def send_async_no_object(email_module_name, email_class_name, object, args, kwargs):
    email_module = importlib.import_module(email_module_name)
    email_class = getattr(email_module, email_class_name)
    email_class().dispatch(object, *args, **kwargs)
