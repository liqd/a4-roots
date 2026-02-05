"""Provider implementation for AI services."""

from abc import ABC
from pathlib import Path

from django.conf import settings
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.messages import BinaryContent
from pydantic_ai.messages import BinaryImage
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider


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

        # All providers are OpenAI-compatible
        # Create OpenAIProvider directly with base_url and api_key
        provider = OpenAIProvider(
            base_url=config.base_url,
            api_key=config.api_key,
        )

        # Use OpenAIChatModel for regular text requests (compatible with all providers)
        self.model = OpenAIChatModel(
            model_name=config.model_name,
            provider=provider,
        )

        # Use OpenAIResponsesModel for image/PDF requests (better handling of file annotations)
        self.responses_model = OpenAIResponsesModel(
            model_name=config.model_name,
            provider=provider,
        )

    def request(self, request: AIRequest, result_type: type[BaseModel]) -> BaseModel:
        """
        Execute a request with structured input and output.

        Args:
            request: Pydantic BaseModel with request data
            result_type: Pydantic BaseModel class for structured output

        Returns:
            Structured response as BaseModel instance
        """
        # Get system prompt from settings
        system_prompt = getattr(
            settings,
            "SYSTEM_PROMPT",
            "",
        )

        # Create agent with output_type for structured output
        agent = Agent(
            model=self.model,
            system_prompt=system_prompt,
            output_type=result_type,
        )

        # Convert request to prompt string using prompt() method
        result = agent.run_sync(request.prompt())
        # result.output is already an instance of result_type
        response = result.output

        # Set provider handle if response has provider field
        if hasattr(response, "provider"):
            response.provider = self.config.handle

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
        # Get system prompt from settings
        system_prompt = getattr(
            settings,
            "SYSTEM_PROMPT",
            "",
        )

        # Create agent with output_type for structured output
        # Use OpenAIResponsesModel for image/PDF requests (better handling of file annotations)
        # Increase output_retries for vision requests as they may need more attempts
        agent = Agent(
            model=self.responses_model,
            system_prompt=system_prompt,
            output_type=result_type,
            output_retries=3,  # Allow more retries for vision output validation
        )

        # Ensure path is a Path object
        doc_path = Path(doc_path) if not isinstance(doc_path, Path) else doc_path

        # Read file and create BinaryImage or BinaryContent object
        file_contents = []
        if not doc_path.exists():
            raise FileNotFoundError(f"File not found: {doc_path}")

        # Determine media type from file extension
        ext = doc_path.suffix.lower()
        media_type_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".pdf": "application/pdf",
        }
        media_type = media_type_map.get(ext, "image/jpeg")

        # Read file
        with open(doc_path, "rb") as f:
            file_data = f.read()

        # Use BinaryImage for images, BinaryContent for PDFs and other documents
        if media_type.startswith("image/"):
            file_contents.append(BinaryImage(data=file_data, media_type=media_type))
        else:
            # For PDFs and other documents, use BinaryContent
            file_contents.append(BinaryContent(data=file_data, media_type=media_type))

        # Combine prompt text with files as UserContent sequence
        user_content = [request.prompt()] + file_contents

        # Run with user_content (not images parameter)
        result = agent.run_sync(user_content)
        # result.output is already an instance of result_type
        response = result.output

        # Set provider handle if response has provider field
        if hasattr(response, "provider"):
            response.provider = self.config.handle

        return response
