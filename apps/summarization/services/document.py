"""Document and image processing service."""

import logging

from sentry_sdk import capture_exception

from ..pydantic_models import DocumentInputItem
from ..pydantic_models import DocumentSummaryItem
from ..pydantic_models import DocumentSummaryResponse
from ..requests.document import MultimodalSummaryRequest
from ..utils import extract_text_from_document
from .base import AIServiceBase

logger = logging.getLogger(__name__)


class DocumentProcessor(AIServiceBase):
    """Service for processing documents and images."""

    def __init__(self, provider_handle: str = None):
        """Initialize document processor with provider."""
        super().__init__(provider_handle, "AI_DOCUMENT_PROVIDER")

    def request_vision_dict(
        self, documents_dict: dict[str, str], prompt: str | None = None
    ) -> DocumentSummaryResponse:
        """Process documents from dictionary format."""
        items = [DocumentInputItem(handle=h, url=u) for h, u in documents_dict.items()]
        return self.request_vision(items, prompt)

    def request_vision(
        self, documents: list[DocumentInputItem], prompt: str | None = None
    ) -> DocumentSummaryResponse:
        """Process documents and images, return combined summaries."""
        docs, images = self._split_documents(documents)

        results = []
        if docs[0]:
            results.extend(self._process_documents(docs))
        if images[0]:
            results.extend(self._process_images(images, prompt))

        return DocumentSummaryResponse(documents=results)

    def _split_documents(self, documents):
        """Split into regular docs and images."""
        docs_urls, docs_handles = [], []
        img_urls, img_handles = [], []

        for doc in documents:
            if not self.provider.config.supports_documents and doc.is_document():
                docs_urls.append(doc.url)
                docs_handles.append(doc.handle)
            else:
                img_urls.append(doc.url)
                img_handles.append(doc.handle)

        return (docs_urls, docs_handles), (img_urls, img_handles)

    def _process_documents(self, docs_data):
        """Extract text from PDFs/DOCX files."""
        urls, handles = docs_data
        results = []

        for url, handle in zip(urls, handles):
            try:
                text = extract_text_from_document(url)
                results.append(DocumentSummaryItem(handle=handle, summary=text))
            except Exception as e:
                logger.error(
                    f"Failed to extract text from {handle}: {e}", exc_info=True
                )
                capture_exception(e)

        return results

    def _process_images(self, images_data, prompt):
        """Process images with vision API."""
        urls, handles = images_data

        if not prompt:
            prompt = (
                f"Summarize each image separately. Handles in order: {handles}. "
                f"Return list of summaries with handles."
            )

        request = MultimodalSummaryRequest(image_urls=urls, prompt=prompt)
        response = self.provider.request(request, DocumentSummaryResponse)
        return response.documents
