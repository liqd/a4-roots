import os
import tempfile

from django.conf import settings
from django.shortcuts import render
from django.views import View

from .services import AIService
from .services import ImageSummaryRequest
from .services import SummaryRequest
from .services import SummaryResponse


class SummarizationTestView(View):
    """Simple test view for summarization service."""

    def get(self, request):
        """Display test form."""
        return render(request, "summarization/test.html")

    def post(self, request):
        """Process summarization request."""
        text = request.POST.get("text", "")
        max_length = int(request.POST.get("max_length", 500))
        provider_handle = request.POST.get("provider", None)
        uploaded_file = request.FILES.get("image", None)

        context = {
            "text": text,
            "max_length": max_length,
            "provider": provider_handle or "openrouter",
            "summary": None,
            "error": None,
            "key_points": None,
            "original_length": 0,
            "summary_length": 0,
        }

        # Handle image upload
        if uploaded_file:
            # Validate file type
            allowed_types = getattr(
                settings, "SUMMARIZATION_ALLOWED_IMAGE_TYPES", [".png", ".jpg", ".jpeg"]
            )
            file_ext = os.path.splitext(uploaded_file.name)[1].lower()
            if file_ext not in allowed_types:
                context["error"] = f"Unsupported file type: {file_ext}. Allowed types: {', '.join(allowed_types)}"
                return render(request, "summarization/test.html", context)

            # Validate file size
            max_size = getattr(settings, "SUMMARIZATION_MAX_FILE_SIZE", 10 * 1024 * 1024)  # 10MB default
            if uploaded_file.size > max_size:
                context["error"] = f"File too large: {uploaded_file.size} bytes. Maximum: {max_size} bytes"
                return render(request, "summarization/test.html", context)

            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                for chunk in uploaded_file.chunks():
                    tmp_file.write(chunk)
                tmp_file_path = tmp_file.name

            try:
                service = AIService(provider_handle=provider_handle)
                summary = service.summarize_image(tmp_file_path, max_length=max_length)
                context["summary"] = summary
                context["summary_length"] = len(summary)
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
                summary_request = SummaryRequest(text=text, max_length=max_length)
                response = service.provider.request(summary_request, result_type=SummaryResponse)
                context["summary"] = response.summary
                context["key_points"] = response.key_points
                context["original_length"] = len(text)
                context["summary_length"] = len(response.summary)
            except Exception as e:
                context["error"] = str(e)

        return render(request, "summarization/test.html", context)
