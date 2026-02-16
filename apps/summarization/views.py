from django.shortcuts import render
from django.views import View

from .pydantic_models import DocumentInputItem
from .pydantic_models import ProjectSummaryResponse
from .services import AIService
from .services import MultimodalSummaryRequest
from .services import SummaryRequest
from .utils import extract_image_urls_from_json


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

    def _collect_image_urls(
        self, image_urls_input: str, json_data: str
    ) -> tuple[list[str], str | None]:
        """Collect image URLs from input fields."""
        image_urls = []

        if image_urls_input:
            urls = [
                url.strip()
                for url in image_urls_input.replace("\n", ",").split(",")
                if url.strip()
            ]
            image_urls.extend(urls)

        if json_data:
            try:
                extracted_urls = extract_image_urls_from_json(json_data)
                image_urls.extend(extracted_urls)
            except Exception as e:
                return [], f"Error extracting URLs from JSON: {str(e)}"

        return list(dict.fromkeys(image_urls)), None

    def _handle_multimodal_request(
        self, image_urls: list[str], text: str, prompt: str, provider_handle: str | None
    ) -> tuple[ProjectSummaryResponse | None, list[str], str | None]:
        """Handle multimodal request with images."""
        try:
            service = AIService(provider_handle=provider_handle)
            request_object = MultimodalSummaryRequest(
                image_urls=image_urls,
                text=text if text else None,
                prompt=prompt if prompt else None,
            )
            response = service.summarize_generic(
                request_object=request_object,
                result_type=ProjectSummaryResponse,
            )
            return response, image_urls, None
        except Exception as e:
            return None, image_urls, str(e)

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
        image_urls_input = request.POST.get("image_urls", "")
        json_data = request.POST.get("json_data", "")

        context = {
            "text": text,
            "prompt": prompt,
            "default_prompt": SummaryRequest.DEFAULT_PROMPT,
            "provider": provider_handle or "ovhcloud",
            "summary_response": None,
            "error": None,
            "original_length": 0,
        }

        image_urls, error = self._collect_image_urls(image_urls_input, json_data)
        if error:
            context["error"] = error
            return render(request, "summarization/test.html", context)

        if image_urls:
            response, image_urls_result, error = self._handle_multimodal_request(
                image_urls, text, prompt, provider_handle
            )
            context["summary_response"] = response
            context["image_urls"] = image_urls_result
            if error:
                context["error"] = error
        elif text:
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
            "provider": provider_handle or "routerlab",
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
