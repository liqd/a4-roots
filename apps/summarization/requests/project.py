"""Project-specific AI requests."""

from .base import AIRequest


class SummaryRequest(AIRequest):
    """Request model for text summarization."""

    DEFAULT_PROMPT = """
You are a JSON generator. Return ONLY valid JSON.

Schema:
{
  "title": "Summary of participation",
  "general_info": {"summary": "string", "goals": ["string"]},
  "phases": {
    "past": {"modules": [{"module_id": "number", "module_name": "string", "status": "past", "final": {"summary": "string", "bullets": ["string"]}, "debug": {...}}]},
    "current": {"modules": [{"module_id": "number", "module_name": "string", "status": "current", "final": {"summary": "string", "bullets": ["string"]}, "debug": {...}}]},
    "upcoming": {"modules": [{"module_id": "number", "module_name": "string", "status": "upcoming", "final": {"summary": "string", "bullets": ["string"]}, "debug": {...}}]}
  }
}

NOTE: module_id in the output should match the given module_id of the input for each module

Each module MUST include a 'debug' object with:
- module_type: string
- signals_snapshot: list of strings
- draft_before_qa: string
- claims: list of {claim_text, evidence_type(from_votes|from_ratings|from_open_answers|from_comments|from_base_text|uncertain), action(keep|soften|remove), fix_hint}
- quantifier_fixes: list of {original_phrase, replacement, reason}
- anchors: list of strings
- coverage_gaps: list of strings
- coverage_patch: optional string
- patches: list of {patch_type(REPLACE|REMOVE|ADD_SENTENCE), target, replacement}
- after_qa: string
- diff_summary: optional string
- qa_status: PASS|FAIL

Extract real data from the project export.
Respond with ONLY the JSON object.
"""

    def __init__(self, text: str, prompt: str | None = None):
        super().__init__()
        self.text = text
        self.prompt_text = prompt or self.DEFAULT_PROMPT

    def prompt(self) -> str:
        return f"{self.prompt_text}\n\n{self.text}"
