import os
import tempfile

from django.conf import settings
from django.shortcuts import render
from django.views import View

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

    def post(self, request):
        """Process summarization request."""
        text = request.POST.get("text", "")
        prompt = request.POST.get("prompt", "")
        provider_handle = request.POST.get("provider", None)
        uploaded_file = request.FILES.get("doc", None)

        default_prompt = SummaryRequest.DEFAULT_PROMPT

        context = {
            "text": text,
            "prompt": prompt,
            "default_prompt": default_prompt,
            "provider": provider_handle or "ovhcloud",
            "summary_response": None,
            "error": None,
            "original_length": 0,
        }

        # Handle document/image upload
        if uploaded_file:
            # Validate file type
            allowed_types = getattr(
                settings, "SUMMARIZATION_ALLOWED_IMAGE_TYPES", [".png", ".jpg", ".jpeg"]
            )
            file_ext = os.path.splitext(uploaded_file.name)[1].lower()
            if file_ext not in allowed_types:
                context["error"] = (
                    f"Unsupported file type: {file_ext}. Allowed types: {', '.join(allowed_types)}"
                )
                return render(request, "summarization/test.html", context)

            # Validate file size
            max_size = getattr(
                settings, "SUMMARIZATION_MAX_FILE_SIZE", 10 * 1024 * 1024
            )  # 10MB default
            if uploaded_file.size > max_size:
                context["error"] = (
                    f"File too large: {uploaded_file.size} bytes. Maximum: {max_size} bytes"
                )
                return render(request, "summarization/test.html", context)

            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                for chunk in uploaded_file.chunks():
                    tmp_file.write(chunk)
                tmp_file_path = tmp_file.name

            try:
                service = AIService(provider_handle=provider_handle)
                response = service.multimodal_summarize(
                    tmp_file_path,
                    text=text if text else None,
                    prompt=prompt if prompt else None,
                    result_type=ProjectSummaryResponse,
                )
                context["summary_response"] = response
                context["uploaded_filename"] = uploaded_file.name
            except Exception as e:
                context["error"] = str(e)
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)

        # Handle text summarization
        elif text:
            try:
                service = AIService(provider_handle=provider_handle)
                response = service.summarize(
                    text=text,
                    prompt=prompt if prompt else None,
                    result_type=ProjectSummaryResponse,
                )
                context["summary_response"] = response
                context["original_length"] = len(text)
            except Exception as e:
                context["error"] = str(e)

        return render(request, "summarization/test.html", context)
