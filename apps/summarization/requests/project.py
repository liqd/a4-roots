"""Project-specific AI requests."""

import json
from typing import Any
from typing import Dict
from typing import List

from .base import AIRequest


class ModuleSummaryRequest(AIRequest):
    """Request for summarizing a single module."""

    PROMPT_TEMPLATE = """
    Summarize this participation module:

    Module: {module_name}
    Phase: {phase}
    Description: {description}
    Data: {content}

    Return ONLY valid JSON with EXACTLY this format:
    {{
      "summary": "A 2-3 sentence overview of what happened in this module",
      "bullets": [
        "Key point 1 about specific contributions",
        "Key point 2 about ideas or proposals",
        "Key point 3 about engagement or outcomes"
      ]
    }}

  The response MUST include BOTH "summary" and "bullets" fields.
  "bullets" MUST be an array of strings, never empty.
  """

    def __init__(self, module_data: Dict[str, Any], phase: str):
        super().__init__()
        self.module_data = module_data
        self.phase = phase

    def prompt(self) -> str:
        """Generate the prompt for this module."""
        return self.PROMPT_TEMPLATE.format(
            module_name=self.module_data.get("module_name", "Unknown"),
            phase=self.phase,
            description=self.module_data.get("description", "No description"),
            content=json.dumps(self.module_data.get("content", {})),
        )


class GeneralInfoRequest(AIRequest):
    """Request for project-level summary."""

    PROMPT_TEMPLATE = """
    Summarize this entire project:

    Project: {project_name}
    Description: {description}
    Module Summaries: {module_summaries}

    Return ONLY valid JSON with EXACTLY this format:
    {{
      "summary": "A 3-4 sentence overview of the entire project's participation",
      "goals": [
        "First main goal or theme",
        "Second main goal or theme",
        "Third main goal or theme"
      ]
    }}

    The response MUST include BOTH "summary" and "goals" fields.
    "goals" MUST be an array of strings, at least 2-3 items.
    """

    def __init__(
        self, project_data: Dict[str, Any], module_summaries: List[Dict[str, Any]]
    ):
        super().__init__()
        self.project_data = project_data
        self.module_summaries = module_summaries

    def prompt(self) -> str:
        """Generate the prompt for project summary."""
        project = self.project_data.get("project", {})
        return self.PROMPT_TEMPLATE.format(
            project_name=project.get("name", "Unknown"),
            description=project.get("information", "No description"),
            module_summaries=json.dumps(self.module_summaries),
        )


class SummaryRequest(AIRequest):
    """Legacy request model for text summarization."""

    DEFAULT_PROMPT = """
    You are a JSON generator. Return ONLY valid JSON.

    Schema:
    {
      "title": "Summary of participation",
      "general_info": {"summary": "string", "goals": ["string"]},
      "phases": {
        "past": {"modules": [{"module_id": "number", "module_name": "string", "status": "past", "final": {"summary": "string", "bullets": ["string"]}}]},
        "current": {"modules": [{"module_id": "number", "module_name": "string", "status": "current", "final": {"summary": "string", "bullets": ["string"]}}]},
        "upcoming": {"modules": [{"module_id": "number", "module_name": "string", "status": "upcoming", "final": {"summary": "string", "bullets": ["string"]}}]}
      }
    }

    NOTE: module_id in the output should match the given module_id of the input for each module

    Extract real data from the project export.
    Respond with ONLY the JSON object.
    """

    def __init__(self, text: str, prompt: str | None = None):
        super().__init__()
        self.text = text
        self.prompt_text = prompt or self.DEFAULT_PROMPT

    def prompt(self) -> str:
        return f"{self.prompt_text}\n\n{self.text}"
