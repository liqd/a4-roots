# Summarization Service

AI-powered text summarization service using OpenAI-compatible providers.

## Setup

Copy `adhocracy-plus/config/settings/local.py.template` to `adhocracy-plus/config/settings/local.py` and configure your API keys.


## Usage

```python
from apps.summarization.services import AIService

service = AIService(provider_handle="openrouter")
summary = service.summarize(text="Long text...", max_length=500)
```

## Testing

Run manual test:
```bash
venv/bin/python manage.py shell < apps/summarization/test_summarization.py
# or
venv/bin/python apps/summarization/test_summarization.py --provider openrouter
```

## Web Interface

A web-based test interface is available at `/summarization/test/` for interactive testing of the summarization service. 


