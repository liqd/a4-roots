from django.shortcuts import render
from django.views import View

from .services import AIService
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

        context = {
            "text": text,
            "max_length": max_length,
            "provider": provider_handle or "openrouter",
            "summary": None,
            "error": None,
        }

        if text:
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
