# Summarization Service

AI-powered text summarization service using OpenAI-compatible providers.

## Setup

Copy `adhocracy-plus/config/settings/local.py.template` to `adhocracy-plus/config/settings/local.py` and configure your API keys.


## Usage

### Basic Text Summarization

```python
from apps.summarization.services import AIService

service = AIService(provider_handle="openrouter")
summary = service.summarize(text="Long text...")
```

### Document and Image Summarization with Vision API

```python
from apps.summarization.services import AIService
from apps.summarization.pydantic_models import DocumentInputItem

service = AIService(document_provider_handle="mistral")

# Prepare documents (PDFs, DOCX, images)
documents = [
    DocumentInputItem(handle="doc1", url="https://example.com/document.pdf"),
    DocumentInputItem(handle="img1", url="https://example.com/image.jpg"),
]

# Process documents and images
vision_response = service.request_vision(documents=documents)

# Extract summaries from vision response
document_summaries = []
for doc in vision_response.documents:
    document_summaries.append(f"{doc.handle}: {doc.summary}")

# Combine with text content
combined_text = "\n\n".join(document_summaries) + "\n\nAdditional text content..."

# Summarize everything together
final_summary = service.summarize(text=combined_text)
```

## Testing

Run manual test:
```bash
venv/bin/python manage.py shell < apps/summarization/test_summarization.py
# or
venv/bin/python apps/summarization/test_summarization.py --provider openrouter
```


## Caching / Celery Beat

- **Caching (exact match & rate limiting)**: `AIService.project_summarize` stores each successful project summary as a `ProjectSummary` with an `input_text_hash`. On later calls (from Celery Beat or the web UI) the service first checks for an exact hash match; if it finds one, the stored summary is reused.
- **Celery Beat as the only AI entry point**: Actual AI calls for project summaries are triggered exclusively by the periodic Celery Beat task, not by the "Generate AI summary" button in the UI. The Beat job runs every 30 minutes (when configured via `CELERY_BEAT_SCHEDULE`) and enqueues `generate_project_summary_task` for eligible projects.
- **Change detection vs. staleness**: When the Celery job runs for a project, the current export content is hashed and compared with the last stored `input_text_hash`:
  - If the content has changed, a **new AI summary** is generated and a new `ProjectSummary` row with a fresh `created_at` timestamp is stored.
  - If the content has **not** changed, no new AI request is sent; instead, only the existing summary's `last_checked_at` field is updated to the current time to confirm that the summary is still up to date.
- **Button behaviour in the UI**: Clicking the "Generate AI summary" button no longer triggers a direct AI request. It refreshes the project export, performs the same hash-based check as above and, when the existing summary is still valid (no content changes), updates `last_checked_at` to the current time.
- **Where timestamps are shown**:
  - `last_checked_at` is displayed directly on the project page.
  - `created_at` is currently only visible in the browser’s JavaScript console (F12) in the summary debug output.


## Configuration options (settings)

- `AI_PROVIDER` / `AI_DOCUMENT_PROVIDER`: Default providers for text and document summarization (see `local.py.template`).
- `PROJECT_SUMMARY_AUTO_REFRESH_MAX_AGE_MINUTES`: Maximum age (in minutes) before the periodic job (`refresh_project_summaries`) is allowed to generate a new project summary.
- `PROJECT_SUMMARY_AUTO_REFRESH_MAX_PROJECTS_PER_RUN`: Maximum number of projects processed per 30‑minute run of the periodic job (`0` = no limit).
- Celery Beat: to enable the periodic refresh (and thus all real AI summarization for project summaries), add `refresh_project_summaries` to `CELERY_BEAT_SCHEDULE` in your `local.py` (see commented example in `local.py.template`).

## Web Interface

Two web-based test interfaces are available for interactive testing:

- `/summarization/test/` - Test interface for text and image summarization
- `/summarization/test-documents/` - Test interface for document summarization with handles (supports PDF, DOCX, and images) 
- `/ORGA_SLUG/projects/PROJECT_SLUG/generate-summary-test/` - internal test URL that triggers summary generation for a single project in the same way as the Celery Beat task (replace slugs and domain as appropriate).


