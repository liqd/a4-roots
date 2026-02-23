"""Generic key-value settings stored in DB, editable in Django Admin."""

from django.db import models


class Settings(models.Model):
    """
    Key-value config store (e.g. for prompts, feature flags).
    Only keys listed in REGISTRY (below) are known; default must be set there.
    get_value(key) uses the registry default and auto-creates a DB row if missing.
    """

    key = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Key",
        help_text="Unique identifier for this setting (e.g. project_summary_prompt).",
    )
    value = models.TextField(
        blank=True,
        default="",
        verbose_name="Value",
        help_text="Stored value. Empty value falls back to the default from the registry.",
    )

    class Meta:
        verbose_name = "Setting"
        verbose_name_plural = "Settings"
        ordering = ["key"]

    def __str__(self):
        return self.key

    @classmethod
    def get_value(cls, key: str) -> str | None:
        """
        Return the value for key. Only keys in REGISTRY are supported.

        - If key is not in REGISTRY: return None (no auto-create).
        - If key is in REGISTRY but no DB row exists: create row with default from REGISTRY, return that default.
        - If DB row exists: return its value (stripped), or the registry default if value is empty.
        """
        if key not in REGISTRY:
            return None
        default = REGISTRY[key].get("default") or ""
        try:
            obj = cls.objects.get(key=key)
        except cls.DoesNotExist:
            cls.objects.create(key=key, value=default)
            return default
        raw = (obj.value or "").strip()
        return raw if raw else default

    @classmethod
    def get_registry_default(cls, key: str) -> str | None:
        """Return the default for key from REGISTRY (for display in admin). Returns None if key unknown."""
        if key not in REGISTRY:
            return None
        return REGISTRY[key].get("default")


# Registry: key -> {"default": str}. Default is required. Add new settings here.
REGISTRY = {
    "project_summary_prompt": {
        "default": """
You are a JSON generator. Return ONLY valid JSON. No explanations, no markdown, no code blocks.

Schema:
{
"title": "Summary of participation",
"stats": {"participants": 0, "contributions": 0, "modules": 0},
"general_summary": "string",
"general_goals": ["string"],
"past_modules": [
    {
    "id": "int",
    "module_id": "int",
    "module_name": "string",
    "purpose": "string",
    "main_sentiments": ["string"],
    "phase_status": "past",
    "link": "string"
    }
],
"current_modules": [
    {
    "id": "int",
    "module_id": "int",
    "module_name": "string",
    "purpose": "string",
    "first_content": ["string"],
    "phase_status": "active",
    "link": "string"
    }
],
"upcoming_modules": [
    {
    "id": "int",
    "module_id": "int",
    "module_name": "string",
    "purpose": "string",
    "phase_status": "upcoming",
    "link": "string"
    }
]
}

Extract real data from the project export. Use actual numbers and content.
Respond with ONLY the JSON object.
""".strip()
    },
}
