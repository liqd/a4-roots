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

- **Caching (exact match & rate limiting)**: `AIService.project_summarize` stores each successful project summary as a `ProjectSummary` with an `input_text_hash`. Auf späteren Aufrufen wird zuerst auf einen exakten Hash-Treffer geprüft; bei Übereinstimmung wird die gespeicherte Zusammenfassung verwendet und das Feld `last_checked_at` aktualisiert. Zusätzlich können projektbezogene und globale Rate-Limits aktiv sein, bei denen innerhalb kurzer Intervalle ebenfalls die letzte Summary wiederverwendet wird (ohne `last_checked_at` zu ändern).
- **Periodic refresh via Celery Beat (`refresh_project_summaries`)**: Ein optionaler periodischer Celery-Task kann `generate_project_summary_task` für Projekte einreihen, die keine Summary jünger als `PROJECT_SUMMARY_AUTO_REFRESH_MAX_AGE_MINUTES` haben. Dank der Hash‑basierten Caching-Logik werden nur Projekte, deren Exportinhalt sich tatsächlich geändert hat (oder deren Summary explizit erneuert werden darf), eine neue AI-Anfrage auslösen.


## Configuration options (settings)

- `AI_PROVIDER` / `AI_DOCUMENT_PROVIDER`: Default providers for text and document summarization (see `local.py.template`).
- `PROJECT_SUMMARY_AUTO_REFRESH_MAX_AGE_MINUTES`: Maximum age (in minutes) before the periodic job (`refresh_project_summaries`) is allowed to generate a new project summary.
- `PROJECT_SUMMARY_AUTO_REFRESH_MAX_PROJECTS_PER_RUN`: Maximum number of projects processed per 30‑minute run of the periodic job (`0` = no limit).
- Celery Beat: to enable the periodic refresh, add `refresh_project_summaries` to `CELERY_BEAT_SCHEDULE` in your `local.py` (see commented example in `local.py.template`).

## Web Interface

Two web-based test interfaces are available for interactive testing:

- `/summarization/test/` - Test interface for text and image summarization
- `/summarization/test-documents/` - Test interface for document summarization with handles (supports PDF, DOCX, and images) 


