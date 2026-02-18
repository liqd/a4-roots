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

## Web Interface

Two web-based test interfaces are available for interactive testing:

- `/summarization/test/` - Test interface for text and image summarization
- `/summarization/test-documents/` - Test interface for document summarization with handles (supports PDF, DOCX, and images) 


