from django.shortcuts import render
from django.views import View

from .pydantic_models import DocumentInputItem
from .pydantic_models import ProjectSummaryResponse
from .services import AIService
from .services import SummaryRequest


class SummarizationTestView(View):
    """Simple test view for summarization service."""

    def get(self, request):
        """Display test form."""
        # Use multimodal default prompt as it's more general
        default_prompt = SummaryRequest.DEFAULT_PROMPT
        context = {
            "default_prompt": default_prompt,
        }
        return render(request, "summarization/test.html", context)

    def _handle_text_request(
        self, text: str, prompt: str, provider_handle: str | None
    ) -> tuple[ProjectSummaryResponse | None, int, str | None]:
        """Handle text-only summarization."""
        try:
            service = AIService(provider_handle=provider_handle)
            response = service.summarize(
                text=text,
                prompt=prompt if prompt else None,
                result_type=ProjectSummaryResponse,
            )
            return response, len(text), None
        except Exception as e:
            return None, 0, str(e)

    def post(self, request):
        """Process summarization request."""
        text = request.POST.get("text", "")
        prompt = request.POST.get("prompt", "")
        provider_handle = request.POST.get("provider", None)

        context = {
            "text": text,
            "prompt": prompt,
            "default_prompt": SummaryRequest.DEFAULT_PROMPT,
            "provider": provider_handle or "ovhcloud",
            "summary_response": None,
            "error": None,
            "original_length": 0,
        }

        if text:
            response, original_length, error = self._handle_text_request(
                text, prompt, provider_handle
            )
            context["summary_response"] = response
            context["original_length"] = original_length
            if error:
                context["error"] = error

        return render(request, "summarization/test.html", context)


class DocumentSummarizationTestView(View):
    """Test view for document summarization with handles."""

    def get(self, request):
        """Display test form."""
        context = {}
        return render(request, "summarization/test_documents.html", context)

    def post(self, request):
        """Process document summarization request."""
        prompt = request.POST.get("prompt", "")
        provider_handle = request.POST.get("provider", None)
        if provider_handle == "":
            provider_handle = None
        documents_json = request.POST.get("documents", "")

        context = {
            "prompt": prompt,
            "provider": provider_handle or "ovhcloud",
            "documents_json": documents_json,
            "summary_response": None,
            "error": None,
        }

        if documents_json:
            try:
                import json

                # Parse JSON input
                documents_data = json.loads(documents_json)

                # Convert to list of DocumentInputItem
                if isinstance(documents_data, dict):
                    # If it's a dict, convert to list format
                    documents = [
                        DocumentInputItem(handle=handle, url=url)
                        for handle, url in documents_data.items()
                    ]
                elif isinstance(documents_data, list):
                    # If it's already a list
                    documents = [
                        DocumentInputItem(**doc) if isinstance(doc, dict) else doc
                        for doc in documents_data
                    ]
                else:
                    raise ValueError("Documents must be a dict or list")

                # Process documents
                service = AIService(document_provider_handle=provider_handle)
                response = service.request_vision(
                    documents=documents,
                    prompt=prompt if prompt else None,
                )
                context["summary_response"] = response

            except json.JSONDecodeError as e:
                context["error"] = f"Invalid JSON: {str(e)}"
            except Exception as e:
                context["error"] = str(e)
        else:
            context["error"] = "Please provide documents in JSON format"

        return render(request, "summarization/test_documents.html", context)
