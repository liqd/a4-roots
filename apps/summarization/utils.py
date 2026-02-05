"""Utility functions for document processing."""

from pathlib import Path

from pydantic_ai.messages import BinaryContent
from pydantic_ai.messages import BinaryImage


def read_document(doc_path: Path) -> BinaryImage | BinaryContent:
    """
    Read a document file and return appropriate content object.

    Args:
        doc_path: Path to the document/image file

    Returns:
        BinaryImage or BinaryContent object

    Raises:
        FileNotFoundError: If file does not exist
    """
    # Ensure path is a Path object
    doc_path = Path(doc_path) if not isinstance(doc_path, Path) else doc_path

    if not doc_path.exists():
        raise FileNotFoundError(f"File not found: {doc_path}")

    # Determine media type from file extension
    ext = doc_path.suffix.lower()
    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".pdf": "application/pdf",
    }
    media_type = media_type_map.get(ext, "image/jpeg")

    # Read file
    with open(doc_path, "rb") as f:
        file_data = f.read()

    # Use BinaryImage for images, BinaryContent for PDFs and other documents
    if media_type.startswith("image/"):
        return BinaryImage(data=file_data, media_type=media_type)
    else:
        # For PDFs and other documents, use BinaryContent
        return BinaryContent(data=file_data, media_type=media_type)
