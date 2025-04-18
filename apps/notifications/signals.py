from django.contrib.auth import get_user_model
from django.db.models import signals
from django.dispatch import receiver

from adhocracy4.actions.models import Action
from adhocracy4.actions.verbs import Verbs
from adhocracy4.dashboard import signals as dashboard_signals
from adhocracy4.follows.models import Follow
from adhocracy4.projects.models import Project
from apps.moderatorfeedback.models import ModeratorCommentFeedback

from . import emails


@receiver(signals.post_save, sender=Action)
def send_notifications(instance, created, **kwargs):
    action = instance
    verb = Verbs(action.verb)

    if action.type in ("item", "comment") and verb in (Verbs.CREATE, Verbs.ADD):
        emails.NotifyCreatorEmail.send(action)

        if action.project:
            emails.NotifyModeratorsEmail.send(action)

    elif action.type == "phase":
        if verb == Verbs.START:
            emails.NotifyFollowersOnPhaseStartedEmail.send(action)
        elif verb == Verbs.SCHEDULE:
            emails.NotifyFollowersOnPhaseIsOverSoonEmail.send(action)

    elif action.type == "offlineevent" and verb == Verbs.START:
        emails.NotifyFollowersOnUpcommingEventEmail.send(action)


@receiver(dashboard_signals.project_created)
def send_project_created_notifications(**kwargs):
    project = kwargs.get("project")
    creator = kwargs.get("user")
    emails.NotifyInitiatorsOnProjectCreatedEmail.send(project, creator_pk=creator.pk)


@receiver(signals.post_delete, sender=Project)
def send_project_deleted_notifications(sender, instance, **kwargs):
    emails.NotifyInitiatorsOnProjectDeletedEmail.send_no_object(instance)


@receiver(signals.post_save, sender=ModeratorCommentFeedback)
def send_moderator_comment_feedback_notification(instance, **kwargs):
    emails.NotifyCreatorOnModeratorCommentFeedback.send(instance)


@receiver(signals.m2m_changed, sender=Project.moderators.through)
def autofollow_project_moderators(instance, action, pk_set, reverse, **kwargs):
    if action == "post_add":
        autofollow_project(instance, pk_set, reverse)


def autofollow_project(instance, pk_set, reverse):
    if not reverse:
        project = instance
        users_pks = pk_set

        for user_pk in users_pks:
            Follow.objects.update_or_create(
                project=project, creator_id=user_pk, defaults={"enabled": True}
            )
    else:
        user = instance
        project_pks = pk_set

        for project_pk in project_pks:
            Follow.objects.update_or_create(
                project_id=project_pk, creator=user, defaults={"enabled": True}
            )
