from ..processing.extractors import extract_comments


def export_poll(poll):
    """Export a single poll with all its data."""
    questions_list = []
    for question in poll.questions.all().order_by("weight"):
        choices_list = []
        for choice in question.choices.all().order_by("weight"):
            votes_list = []
            for vote in choice.votes.all():
                vote_data = {"created": vote.created.isoformat()}
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

    return {
        "id": poll.id,
        "url": poll.get_absolute_url(),
        "questions": questions_list,
        "comments": extract_comments(poll.comments.all()),
        "comment_count": poll.comments.count(),
        "total_votes": sum(q["vote_count"] for q in questions_list),
    }
