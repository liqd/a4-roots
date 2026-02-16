"""Service for text summarization using AI providers."""
import json
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from pydantic import BaseModel

from .models import ProjectSummary
from .providers import AIProvider
from .providers import AIRequest
from .providers import ProviderConfig
from .pydantic_models import ProjectSummaryResponse
from .pydantic_models import SummaryItem
from .pydantic_models import ProjectSummaryResponse
from .pydantic_models import DocumentSummaryResponse
from .pydantic_models import DocumentInputItem
from .pydantic_models import DocumentSummaryItem
from .pydantic_models import DocumentSummaryResponse
from .pydantic_models import ProjectSummaryResponse
from .pydantic_models import SummaryItem
from .utils import extract_text_from_document



PROJECT_SUMMARY_RATE_LIMIT_MINUTES = (
    5  # Minimum minutes between summary generations per project
)
SUMMARY_GLOBAL_LIMIT_PER_HOUR = 100  # Maximum summaries per hour across all projects


class AIService:
    """Service for summarizing text using configured AI provider."""

    def __init__(
        self, provider_handle: str = None, document_provider_handle: str = None
    ):
        """Initialize AI service."""
        provider_handle = provider_handle or getattr(
            settings, "AI_PROVIDER", "openrouter"
        )
        # ProviderConfig loads configuration from settings automatically
        config = ProviderConfig.from_handle(provider_handle)
        self.provider = AIProvider(config)

        # Separate provider for document processing
        # Normalize empty string to None
        if document_provider_handle == "":
            document_provider_handle = None
        document_provider_handle = document_provider_handle or getattr(
            settings, "AI_DOCUMENT_PROVIDER", None
        )
        if document_provider_handle:
            print(f"Using document provider: {document_provider_handle}")
            doc_config = ProviderConfig.from_handle(document_provider_handle)
            print(
                f"Document provider config: model={doc_config.model_name}, base_url={doc_config.base_url}, handle={doc_config.handle}"
            )
            self.document_provider = AIProvider(doc_config)
            print(
                f"Document provider initialized: is_mistral={self.document_provider.is_mistral}"
            )
        else:
            print(
                f"No document provider specified, using default provider: {provider_handle}"
            )
            # Fallback to same provider if no document provider specified
            self.document_provider = self.provider

    def summarize_generic(
        self,
        request_object: AIRequest,
        result_type: type[BaseModel] = SummaryItem,
    ) -> BaseModel:
        print(f"Summarizing generic with request: {request_object.prompt()}")
        response = self.provider.request(request_object, result_type=result_type)
        return response

    def summarize(
        self,
        text: str,
        prompt: str | None = None,
        result_type: type[BaseModel] = SummaryItem,
    ) -> BaseModel:
        """Summarize text."""
        request = SummaryRequest(text=text, prompt=prompt)
        response = self.provider.request(request, result_type=result_type)
        return response

    def project_summarize(
        self,
        project,
        text: str,
        prompt: str | None = None,
        result_type: type[
            BaseModel
        ] = ProjectSummaryResponse,  # Changed from SummaryResponse
        is_rate_limit: bool = True,
    ) -> BaseModel:
        """Summarize text for a project with caching and rate limiting support."""
        request = SummaryRequest(text=text, prompt=prompt)
        # Get the most recent summary for this project (single query for all checks)
        latest_project_summary = (
            ProjectSummary.objects.filter(project=project)
            .order_by("-created_at")
            .first()
        )
        # Only proceed with cache/rate limit checks if project has existing summaries
        if is_rate_limit and latest_project_summary:
            # Check 1: Exact content match
            current_hash = ProjectSummary.compute_hash(text)
            if latest_project_summary.input_text_hash == current_hash:
                print(
                    "****** Cached summary found (exact match via hash comparison) ******"
                )
                return ProjectSummaryResponse(**latest_project_summary.response_data)

            # Check 2: Per-project rate limiting
            time_since_last = timezone.now() - latest_project_summary.created_at
            if time_since_last < timedelta(minutes=PROJECT_SUMMARY_RATE_LIMIT_MINUTES):
                print(
                    f"****** Using rate-limited summary from {latest_project_summary.created_at} (within {PROJECT_SUMMARY_RATE_LIMIT_MINUTES} min per project) ******"
                )
                return ProjectSummaryResponse(**latest_project_summary.response_data)

            # Check 3: Global rate limiting - only if project was last summarized in the last hour
            if time_since_last < timedelta(hours=1):
                global_limit_time = timezone.now() - timedelta(hours=1)
                recent_global_count = ProjectSummary.objects.filter(
                    created_at__gte=global_limit_time
                ).count()

                if recent_global_count >= SUMMARY_GLOBAL_LIMIT_PER_HOUR:
                    print(
                        f"****** Global rate limit reached ({recent_global_count}/{SUMMARY_GLOBAL_LIMIT_PER_HOUR} in last hour) ******"
                    )
                    print(
                        f"****** Using most recent summary from {latest_project_summary.created_at} ******"
                    )
                    return ProjectSummaryResponse(
                        **latest_project_summary.response_data
                    )

        # No existing summary OR all cache/rate limit checks passed - generate new summary
        print("****** Generating new summary ******")
        print(f"Prompt: {request.prompt()[:500]}...")
        response = self.provider.request(request, result_type=result_type)

        # Save to cache if result is ProjectSummaryResponse
        if isinstance(response, ProjectSummaryResponse):
            print(" ------------------ >>>>>>>>>>. CREATED THE PROJECT SUMMARY")
            text = getattr(request, "text", "")
            ProjectSummary.objects.create(
                project=project,
                prompt=request.prompt_text,
                input_text_hash=ProjectSummary.compute_hash(text),
                response_data=json.loads(response.model_dump_json()),
            )
        return response

    def request_vision(
        self,
        documents: list[DocumentInputItem],
        prompt: str | None = None,
    ) -> DocumentSummaryResponse:
        """
        Summarize multiple documents with handles.

        Args:
            documents: List of DocumentInputItem objects, each with handle and url
            prompt: Optional custom prompt for summarization

        Returns:
            DocumentSummaryResponse with list of DocumentSummaryItem objects
        """
        # Check if provider supports documents directly
        document_urls = []
        document_handle_list = []
        image_urls = []
        image_handle_list = []

        for doc in documents:
            if (
                not self.document_provider.config.supports_documents
                and doc.is_document()
            ):
                document_urls.append(doc.url)
                document_handle_list.append(doc.handle)

            else:
                image_urls.append(doc.url)
                image_handle_list.append(doc.handle)

        # Process documents via fallback if needed
        document_results = []
        if len(document_urls):
            results1 = self.request_documents(document_urls, document_handle_list)
            document_results = results1.documents

        # Process images via vision API
        image_results = []
        if len(image_urls):
            results2 = self.request_images(image_urls, image_handle_list, prompt)
            image_results = results2.documents

        # Combine results
        all_results = image_results + document_results

        return DocumentSummaryResponse(documents=all_results)

    def request_images(
        self,
        image_urls: list[str],
        image_handle_list: list[str],
        prompt: str | None = None,
    ) -> DocumentSummaryResponse:
        if prompt:
            custom_prompt = prompt
        else:
            custom_prompt = (
                f"Summarize each document separately. "
                f"The documents are provided in order with the following handles: {image_handle_list}. "
                f"Return a list of summaries, one for each document in the same order. "
                f"Each summary should include the handle and describe the content and most important information of that document."
            )

        request = MultimodalSummaryRequest(
            image_urls=image_urls,
            prompt=custom_prompt,
        )
        return self.document_provider.request(
            request, result_type=DocumentSummaryResponse
        )

    def request_documents(
        self,
        document_urls: list[str],
        document_handle_list: list[str],
    ) -> DocumentSummaryResponse:
        """
        Process documents by extracting text from PDFs and DOCX files.
        
        The extracted text is used directly as the summary, without AI processing.
        
        Args:
            document_urls: List of document URLs
            document_handle_list: List of document handles corresponding to URLs
            
        Returns:
            DocumentSummaryResponse with list of DocumentSummaryItem objects
        """
        results = []
        
        # Process each document
        for url, handle in zip(document_urls, document_handle_list):
            try:
                # Extract text from document
                extracted_text = extract_text_from_document(url)
                
                # Use extracted text directly as summary
                results.append(
                    DocumentSummaryItem(
                        handle=handle,
                        summary=extracted_text,
                    )
                )
            except Exception as e:
                # Create error entry if extraction fails
                error_message = f"Error: {str(e)}"
                results.append(
                    DocumentSummaryItem(
                        handle=handle,
                        summary=error_message,
                    )
                )
        
        return DocumentSummaryResponse(documents=results)


# TODO: Move to a providers.py ?


class SummaryRequest(AIRequest):
    """Request model for text summarization."""

    DEFAULT_PROMPT = """
        You are a JSON generator. Return ONLY valid JSON. No explanations, no markdown, no code blocks.

        Schema:
        {
        "title": "Zusammenfassung der Beteiligung",
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
        """

    def __init__(self, text: str, prompt: str | None = None) -> None:
        super().__init__()
        self.text = text
        self.prompt_text = prompt or self.DEFAULT_PROMPT

    def prompt(self) -> str:
        return f"{self.prompt_text}\n\n{self.text}"


# TODO: Move to a providers.py ?


class MultimodalSummaryRequest(AIRequest):
    """Request model for multimodal document summarization."""

    vision_support = True

    DEFAULT_PROMPT = (
        "Summarize this document/image. "
        "Describe the content and the most important information. "
        "Return your answer as structured JSON that matches the expected format."
    )

    def __init__(
        self,
        image_urls: list[str] | None = None,
        text: str | None = None,
        prompt: str | None = None,
    ) -> None:
        super().__init__()
        self.image_urls = image_urls or []
        self.prompt_text = prompt or self.DEFAULT_PROMPT
        self.text = text

    def prompt(self) -> str:
        if self.text:
            return self.prompt_text + "\n\nText:\n" + self.text
        return self.prompt_text


class DocumentRequest(AIRequest):
    """Request model for document summarization with handle."""

    vision_support = True

    DEFAULT_PROMPT = (
        "Summarize this document. "
        "Describe the content and the most important information. "
        "Return your answer as structured JSON with 'summary' field, "
    )

    def __init__(
        self,
        url: str,
        prompt: str | None = None,
    ) -> None:
        super().__init__()
        self.image_urls = [url]
        self.prompt_text = prompt or self.DEFAULT_PROMPT

    def prompt(self) -> str:
        return self.prompt_text
