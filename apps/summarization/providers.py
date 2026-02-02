"""Provider implementation for AI services."""

from django.conf import settings
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider


class SummaryRequest(BaseModel):
    """Request model for summarization."""

    text: str
    max_length: int = 500


class SummaryResponse(BaseModel):
    """Response model for summarization."""

    summary: str
    provider: str


class ProviderConfig:
    """Configuration for an AI provider."""

    def __init__(
        self,
        api_key: str,
        model_name: str,
        base_url: str,
        handle: str,
    ):
        """
        Initialize provider configuration.

        Args:
            api_key: API key for the provider
            model_name: Name of the model to use
            base_url: Base URL for the API
            handle: Unique identifier/name for this provider configuration
        """
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url
        self.handle = handle

    @classmethod
    def from_handle(cls, handle: str) -> "ProviderConfig":
        """
        Create ProviderConfig from handle by loading configuration from Django settings.

        Args:
            handle: Handle/name of the provider configuration

        Returns:
            ProviderConfig instance

        Raises:
            ValueError: If provider configuration is missing or invalid
        """
        # Get provider configurations from settings
        provider_configs = getattr(settings, "SUMMARIZATION_PROVIDERS", {})

        if not provider_configs:
            raise ValueError(
                "SUMMARIZATION_PROVIDERS not configured. "
                "Please configure providers in local.py"
            )

        if handle not in provider_configs:
            available = ", ".join(provider_configs.keys())
            raise ValueError(
                f"Unknown provider handle: {handle}. "
                f"Available providers: {available}"
            )

        config_dict = provider_configs[handle]

        # Validate required fields
        required_fields = ["api_key", "model_name", "base_url"]
        missing_fields = [field for field in required_fields if field not in config_dict]
        if missing_fields:
            raise ValueError(
                f"Provider configuration '{handle}' is missing required fields: "
                f"{', '.join(missing_fields)}"
            )

        return cls(
            api_key=config_dict["api_key"],
            model_name=config_dict["model_name"],
            base_url=config_dict["base_url"],
            handle=handle,
        )


class AIProvider:
    """Unified provider for AI services using OpenAI-compatible APIs."""

    def __init__(self, config: ProviderConfig):
        """
        Initialize AI provider.

        Args:
            config: Provider configuration object
        """
        self.config = config
        
        # All providers are OpenAI-compatible
        # Create OpenAIProvider directly with base_url and api_key
        provider = OpenAIProvider(
            base_url=config.base_url,
            api_key=config.api_key,
        )
        
        self.model = OpenAIChatModel(
            model_name=config.model_name,
            provider=provider,
        )
        
        self.agent = Agent(
            model=self.model,
            system_prompt="Du bist ein hilfreicher Assistent, der Texte prägnant zusammenfasst.",
        )

    def summarize(self, request: SummaryRequest) -> SummaryResponse:
        """
        Summarize text.

        Args:
            request: Summary request with text and max_length

        Returns:
            SummaryResponse with summary and provider handle
        """
        prompt = (
            f"Fasse den folgenden Text in maximal {request.max_length} Zeichen zusammen:\n\n"
            f"{request.text}"
        )
        result = self.agent.run_sync(prompt)
        # AgentRunResult has output attribute, not data
        summary = str(result.output).strip()
        return SummaryResponse(summary=summary, provider=self.config.handle)
