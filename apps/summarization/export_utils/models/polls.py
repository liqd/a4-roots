from adhocracy4.polls.models import Poll

from ..processing.extractors import extract_comments
from ..processing.module_utils import get_module_status


def export_polls_full(project):
    """Export all polls with full data"""

    polls_data = []
    polls = Poll.objects.filter(module__project=project).prefetch_related(
        "questions__choices__votes__other_vote",
    )

    for poll in polls:
        questions_list = []
        for question in poll.questions.all().order_by("weight"):
            choices_list = []
            for choice in question.choices.all().order_by("weight"):
                votes_list = []
                for vote in choice.votes.all():
                    vote_data = {
                        "created": vote.created.isoformat(),
                    }
                    if hasattr(vote, "other_vote"):
                        vote_data["other_answer"] = vote.other_vote.answer
                    votes_list.append(vote_data)

                choices_list.append(
                    {
                        "label": choice.label,
                        "is_other_choice": choice.is_other_choice,
                        "vote_count": choice.votes.count(),
                        "votes": votes_list,
                    }
                )

            answers_list = []
            for answer in question.answers.all():
                answers_list.append(
                    {
                        "answer": answer.answer,
                        "created": answer.created.isoformat(),
                    }
                )

            questions_list.append(
                {
                    "label": question.label,
                    "multiple_choice": question.multiple_choice,
                    "is_open": question.is_open,
                    "choices": choices_list,
                    "answers": answers_list,
                    "vote_count": sum(c["vote_count"] for c in choices_list),
                }
            )

        # Get comments for this poll
        comments_list = extract_comments(poll.comments.all())

        polls_data.append(
            {
                "id": poll.id,
                "module_id": poll.module.id,
                "active_status": get_module_status(poll.module),
                "module_start": str(poll.module.module_start),
                "module_end": str(poll.module.module_end),
                "description": poll.module.description,
                "url": poll.get_absolute_url(),
                "module_name": poll.module.name,
                "questions": questions_list,
                "comments": comments_list,
                "comment_count": poll.comments.count(),
                "total_votes": sum(q["vote_count"] for q in questions_list),
            }
        )

    return polls_data
