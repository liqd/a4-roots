"""Provider implementation for AI services."""

from abc import ABC
from pathlib import Path

from django.conf import settings
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.mistral import MistralModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.mistral import MistralProvider
from pydantic_ai.providers.openai import OpenAIProvider

from .utils import read_document


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
        provider_configs = getattr(settings, "AI_PROVIDERS", {})

        if not provider_configs:
            raise ValueError(
                "AI_PROVIDERS not configured. " "Please configure providers in local.py"
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
        missing_fields = [
            field for field in required_fields if field not in config_dict
        ]
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


class AIRequest(ABC):
    def prompt(self) -> str:
        raise NotImplementedError("Subclasses must implement prompt()")


class AIProvider:
    """Unified provider for AI services using OpenAI-compatible APIs."""

    def __init__(self, config: ProviderConfig):
        """
        Initialize AI provider.

        Args:
            config: Provider configuration object
        """
        self.config = config

        self.system_prompt = getattr(
            settings,
            "SYSTEM_PROMPT",
            "",
        )

        # Use MistralProvider for Mistral, OpenAIProvider for others
        if config.handle == "mistral":
            self.provider = MistralProvider(
                api_key=config.api_key,
                base_url=config.base_url,
            )
            self.is_mistral = True
        else:
            # All other providers are OpenAI-compatible
            self.provider = OpenAIProvider(
                base_url=config.base_url,
                api_key=config.api_key,
            )
            self.is_mistral = False

    def _set_provider_handle(self, response: BaseModel) -> None:
        """
        Set provider handle on response if it has a provider field.

        Args:
            response: Response object to modify
        """
        if hasattr(response, "provider"):
            response.provider = self.config.handle

    def request(self, request: AIRequest, result_type: type[BaseModel]) -> BaseModel:
        """
        Execute a request with structured input and output.

        Args:
            request: Pydantic BaseModel with request data
            result_type: Pydantic BaseModel class for structured output

        Returns:
            Structured response as BaseModel instance
        """
        # Use MistralModel for Mistral, OpenAIChatModel for others
        if self.is_mistral:
            model = MistralModel(
                self.config.model_name,
                provider=self.provider,
            )
        else:
            model = OpenAIChatModel(
                model_name=self.config.model_name,
                provider=self.provider,
            )

        agent = Agent(
            model=model,
            system_prompt=self.system_prompt,
            output_type=result_type,
            tools=[],  # Disable tool_calls to avoid validation errors with non-standard providers
        )

        result = agent.run_sync(request.prompt())
        response = result.output

        self._set_provider_handle(response)

        return response

    def multimodal_request(
        self, request: AIRequest, result_type: type[BaseModel], doc_path: Path
    ) -> BaseModel:
        """
        Execute a multimodal request with images/PDFs using vision API.

        Args:
            request: Pydantic BaseModel with request data
            result_type: Pydantic BaseModel class for structured output
            doc_path: Path to image or PDF file (Path object)

        Returns:
            Structured response as BaseModel instance
        """
        # Use MistralModel for Mistral, OpenAIResponsesModel for others
        # Note: Mistral may not support vision/multimodal requests
        if self.is_mistral:
            model = MistralModel(
                self.config.model_name,
                provider=self.provider,
            )
        else:
            # Use OpenAIResponsesModel for image/PDF requests (better handling of file annotations)
            model = OpenAIResponsesModel(
                model_name=self.config.model_name,
                provider=self.provider,
            )

        agent = Agent(
            model=model,
            system_prompt=self.system_prompt,
            output_type=result_type,
            output_retries=3,  # Allow more retries for vision output validation
            tools=[],  # Disable tool_calls to avoid validation errors with non-standard providers
        )

        # Read document file and create appropriate content object
        file_content = read_document(doc_path)

        # Combine prompt text with file content as UserContent sequence
        user_content = [request.prompt(), file_content]
        result = agent.run_sync(user_content)
        response = result.output

        self._set_provider_handle(response)

        return response
