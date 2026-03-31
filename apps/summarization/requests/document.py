"""Document and image processing requests."""

from .base import AIRequest


class MultimodalSummaryRequest(AIRequest):
    """Request model for multimodal document summarization."""

    vision_support = True
    PROMPT = "Summarize this image/document. Return JSON with summary field."

    def __init__(
        self, image_urls: list[str], text: str | None = None, prompt: str | None = None
    ):
        super().__init__()
        self.image_urls = image_urls
        self.prompt_text = prompt or self.PROMPT
        self.text = text

    def prompt(self) -> str:
        base = self.prompt_text
        return f"{base}\n\nText:\n{self.text}" if self.text else base


class DocumentRequest(AIRequest):
    """Request model for document summarization."""

    vision_support = True
    PROMPT = "Summarize this document. Return JSON with summary field."

    def __init__(self, url: str, prompt: str | None = None):
        super().__init__()
        self.image_urls = [url]
        self.prompt_text = prompt or self.PROMPT

    def prompt(self) -> str:
        return self.prompt_text
