"""Base classes for AI services."""

import logging

from django.conf import settings
from pydantic import BaseModel

from ..providers import AIProvider
from ..providers import ProviderConfig
from ..requests.project import SummaryRequest

logger = logging.getLogger(__name__)


class AIServiceBase:
    """Base class for AI services with provider initialization."""

    def __init__(self, provider_handle: str = None, settings_key: str = None):
        """Initialize AI service with provider."""
        self.provider = self._init_provider(provider_handle, settings_key)

    def _init_provider(self, handle: str | None, settings_key: str) -> AIProvider:
        """Initialize a provider from handle or settings."""
        if not handle:
            handle = getattr(settings, settings_key, None)
            if not handle:
                raise ValueError(
                    f"No provider configured. Pass {settings_key.lower()} or set {settings_key} in settings."
                )
        return AIProvider(ProviderConfig.from_handle(handle))

    def summarize(
        self,
        text: str,
        prompt: str | None = None,
        result_type: type[BaseModel] = BaseModel,
    ) -> BaseModel:
        """Basic text summarization."""
        request = SummaryRequest(text=text, prompt=prompt)
        return self.provider.request(request, result_type=result_type)
