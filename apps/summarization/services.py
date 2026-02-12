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
from .pydantic_models import DocumentSummaryItem
from .pydantic_models import DocumentInputItem 


PROJECT_SUMMARY_RATE_LIMIT_MINUTES = (
    5  # Minimum minutes between summary generations per project
)
SUMMARY_GLOBAL_LIMIT_PER_HOUR = 100  # Maximum summaries per hour across all projects


class AIService:
    """Service for summarizing text using configured AI provider."""

    def __init__(self, provider_handle: str = None, document_provider_handle: str = None):
        """Initialize AI service."""
        provider_handle = provider_handle or getattr(
            settings, "AI_PROVIDER", "openrouter"
        )
        # ProviderConfig loads configuration from settings automatically
        config = ProviderConfig.from_handle(provider_handle)
        self.provider = AIProvider(config)
        
        # Separate provider for document processing
        document_provider_handle = document_provider_handle or getattr(
            settings, "AI_DOCUMENT_PROVIDER", None
        )
        if document_provider_handle:
            doc_config = ProviderConfig.from_handle(document_provider_handle)
            self.document_provider = AIProvider(doc_config)
        else:
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
        return self.project_summarize_generic(project, request, result_type=result_type)

    def project_summarize_generic(
        self,
        project,
        request: AIRequest,
        result_type: type[BaseModel] = ProjectSummaryResponse,
    ) -> BaseModel:

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
            text = getattr(request, 'text', '')
            ProjectSummary.objects.create(
                project=project,
                prompt=request.prompt_text,
                input_text_hash=ProjectSummary.compute_hash(text),
                response_data=json.loads(response.model_dump_json()),
            )
        return response

    def request_document(
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
        # Collect all URLs and maintain handle mapping
        image_urls = []
        handle_mapping = {}  # Maps URL to handle
        
        for doc in documents:
            image_urls.append(doc.url)
            handle_mapping[doc.url] = doc.handle
        
        # Create a single request with all image URLs
        # Use a custom prompt that includes handles for each document
        if prompt:
            custom_prompt = prompt
        else:
            # Build prompt with handles
            handle_list = ", ".join([f'"{doc.handle}"' for doc in documents])
            custom_prompt = (
                f"Summarize each document separately. "
                f"The documents are provided in order with the following handles: {handle_list}. "
                f"Return a list of summaries, one for each document in the same order. "
                f"Each summary should include the handle and describe the content and most important information of that document."
            )
        
        request = MultimodalSummaryRequest(
            image_urls=image_urls,
            prompt=custom_prompt,
        )
        
        # Use document provider for processing
        # Request DocumentSummaryResponse which contains a list
        try:
            response = self.document_provider.request(
                request,
                result_type=DocumentSummaryResponse,
            )
            
            # Use the summaries directly from response
            # The LLM should have included the handles in the response based on the prompt
            results = response.documents
            
        except Exception as e:
            # If error, create error entries for all documents
            print(f"Error processing documents: {str(e)}")
            results = []
            for doc in documents:
                results.append(
                    DocumentSummaryItem(
                        handle=doc.handle,
                        summary=f"Error: {str(e)}",
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
        "past_summary": "string",
        "past_modules": [
            {
            "module_name": "string",
            "purpose": "string",
            "main_sentiments": ["string"],
            "phase_status": "past",
            "link": "string"
            }
        ],
        "current_summary": "string",
        "current_modules": [
            {
            "module_name": "string",
            "purpose": "string",
            "main_sentiments": ["string"],
            "first_content": "string",
            "phase_status": "active",
            "link": "string"
            }
        ],
        "upcoming_summary": "string",
        "upcoming_modules": [
            {
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
