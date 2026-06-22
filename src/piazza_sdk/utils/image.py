"""Image utility functions for Piazza SDK.

Handles image URL normalization and type detection.
"""

from __future__ import annotations

from urllib.parse import urlparse


def is_image_url(url: str) -> bool:
    """Check if a URL points to an image.

    Args:
        url: URL to check.

    Returns:
        True if URL appears to be an image.
    """
    if not url:
        return False
    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".ico"}
    try:
        parsed = urlparse(url)
        path = parsed.path.lower()
        return any(path.endswith(ext) for ext in image_extensions)
    except (ValueError, TypeError):
        return False


def get_mime_type(url: str) -> str | None:
    """Get MIME type from URL extension.

    Args:
        url: URL to extract MIME type from.

    Returns:
        MIME type string or None if not recognized.
    """
    if not url:
        return None
    ext_to_mime = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
        ".bmp": "image/bmp",
        ".ico": "image/x-icon",
    }
    try:
        parsed = urlparse(url)
        path = parsed.path.lower()
        for ext, mime in ext_to_mime.items():
            if path.endswith(ext):
                return mime
    except (ValueError, TypeError):
        pass
    return None


def detect_image_type(data: bytes) -> str | None:  # noqa: PLR0911
    """Detect image type from binary header.

    Args:
        data: Image file bytes.

    Returns:
        MIME type string or None if not recognized.
    """
    if not data or len(data) < 4:
        return None
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:2] == b"\xff\xd8":
        return "image/jpeg"
    if data[:4] == b"GIF8":
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:5] == b"<?xml" or data[:4] == b"<svg":
        return "image/svg+xml"
    return None


def normalize_image_url(url: str, base_url: str = "") -> str:
    """Normalize an image URL.

    Makes relative URLs absolute and cleans up URL parameters.

    Args:
        url: Image URL (relative or absolute).
        base_url: Base URL for resolving relative URLs.

    Returns:
        Normalized absolute URL.
    """
    if not url:
        return ""

    url = url.strip()

    # If already absolute, return as-is
    if url.startswith(("http://", "https://")):
        return url

    # If relative and we have a base, join them
    if base_url and url.startswith("/"):
        parsed = urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{url}"

    return url
