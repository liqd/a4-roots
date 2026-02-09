"""Django models for summarization."""

import hashlib

from django.db import models
from django.utils import timezone

from adhocracy4.projects.models import Project


class ProjectSummary(models.Model):
    """Stores AI-generated summaries for projects."""

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="summaries",
        verbose_name="Project",
    )
    prompt = models.TextField(
        verbose_name="Prompt",
        help_text="The prompt used for summarization",
    )
    input_text_hash = models.CharField(
        max_length=64,
        db_index=True,
        verbose_name="Input Text Hash",
        help_text="SHA256 hash of the input text for quick comparison",
    )
    response_data = models.JSONField(
        verbose_name="Response Data",
        help_text="The complete SummaryResponse data structure",
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Created At",
        help_text="Timestamp when the summary was created",
    )

    class Meta:
        verbose_name = "Project Summary"
        verbose_name_plural = "Project Summaries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project", "input_text_hash"]),
        ]

    def __str__(self):
        return f"Summary for {self.project} ({self.created_at})"

    @staticmethod
    def compute_hash(text: str) -> str:
        """Compute SHA256 hash of the input text."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @classmethod
    def get_cached_summary(cls, project: Project, prompt: str, input_text: str):
        """
        Get cached summary if it exists for the given project, prompt and input text.

        Args:
            project: The project instance
            prompt: The prompt used
            input_text: The input text to summarize

        Returns:
            ProjectSummary instance or None if not found
        """
        input_hash = cls.compute_hash(input_text)
        return cls.objects.filter(
            project=project, prompt=prompt, input_text_hash=input_hash
        ).first()
