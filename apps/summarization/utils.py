"""Utility functions for document processing."""

import json
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


def extract_image_urls_from_json(json_data: str | dict | list) -> list[str]:
    """
    Extract image URLs from JSON structure.

    Recursively searches through JSON data for URLs that appear to be image URLs.
    Looks for common image URL patterns and fields that might contain image URLs.
    Note: SVG is excluded as it's not supported by most vision models.

    Args:
        json_data: JSON string, dict, or list to search

    Returns:
        List of image URLs found in the JSON structure
    """
    urls = []
    # Supported formats by most vision models (excluding SVG)
    image_extensions = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".tif")
    image_keywords = ("image", "img", "photo", "picture", "url", "src", "href")

    def is_image_url(url: str) -> bool:
        """Check if a string looks like an image URL."""
        if not isinstance(url, str):
            return False
        url_lower = url.lower()
        # Check if it's a valid URL
        if not (url_lower.startswith("http://") or url_lower.startswith("https://")):
            return False
        # Check if it ends with image extension or contains image keywords
        return url_lower.endswith(image_extensions) or any(
            keyword in url_lower for keyword in image_keywords
        )

    def extract_from_value(value):
        """Recursively extract URLs from JSON value."""
        if isinstance(value, str):
            if is_image_url(value):
                urls.append(value)
        elif isinstance(value, dict):
            for key, val in value.items():
                # Check if key suggests it might contain image URLs
                if any(keyword in key.lower() for keyword in image_keywords):
                    if isinstance(val, str) and is_image_url(val):
                        urls.append(val)
                else:
                    extract_from_value(val)
        elif isinstance(value, list):
            for item in value:
                extract_from_value(item)

    # Parse JSON string if needed
    if isinstance(json_data, str):
        try:
            json_data = json.loads(json_data)
        except json.JSONDecodeError:
            return []

    extract_from_value(json_data)
    # Remove duplicates while preserving order
    return list(dict.fromkeys(urls))
