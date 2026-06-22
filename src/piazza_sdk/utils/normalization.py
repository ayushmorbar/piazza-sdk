"""HTML to Markdown normalization utilities for Piazza SDK.

Converts Piazza HTML content to clean Markdown text.
"""

from __future__ import annotations

import html as html_module
import re


def _basic_html_to_markdown(html: str) -> str:
    """Basic HTML to Markdown converter (fallback when html2text unavailable)."""
    text = html

    # Handle common HTML entities
    text = html_module.unescape(text)

    # Convert block-level elements
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<p[^>]*>", "\n\n", text)
    text = re.sub(r"</p>", "", text)
    text = re.sub(r"<div[^>]*>", "\n", text)
    text = re.sub(r"</div>", "", text)
    text = re.sub(r"<h1[^>]*>(.*?)</h1>", r"\n# \1\n", text, flags=re.DOTALL)
    text = re.sub(r"<h2[^>]*>(.*?)</h2>", r"\n## \1\n", text, flags=re.DOTALL)
    text = re.sub(r"<h3[^>]*>(.*?)</h3>", r"\n### \1\n", text, flags=re.DOTALL)
    text = re.sub(r"<h4[^>]*>(.*?)</h4>", r"\n#### \1\n", text, flags=re.DOTALL)
    text = re.sub(r"<h5[^>]*>(.*?)</h5>", r"\n##### \1\n", text, flags=re.DOTALL)
    text = re.sub(r"<h6[^>]*>(.*?)</h6>", r"\n###### \1\n", text, flags=re.DOTALL)

    # Convert inline elements
    text = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", text, flags=re.DOTALL)
    text = re.sub(r"<b[^>]*>(.*?)</b>", r"**\1**", text, flags=re.DOTALL)
    text = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", text, flags=re.DOTALL)
    text = re.sub(r"<i[^>]*>(.*?)</i>", r"*\1*", text, flags=re.DOTALL)
    text = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", text, flags=re.DOTALL)
    text = re.sub(r"<pre[^>]*>(.*?)</pre>", r"\n```\n\1\n```\n", text, flags=re.DOTALL)
    text = re.sub(r"<a[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", r"[\2](\1)", text, flags=re.DOTALL)

    # Convert lists
    text = re.sub(r"<li[^>]*>", "\n- ", text)
    text = re.sub(r"</li>", "", text)
    text = re.sub(r"<ul[^>]*>", "\n", text)
    text = re.sub(r"</ul>", "\n", text)
    text = re.sub(r"<ol[^>]*>", "\n", text)
    text = re.sub(r"</ol>", "\n", text)

    # Convert images
    text = re.sub(r"<img[^>]*src=\"([^\"]+)\"[^>]*/?>", r"![image](\1)", text)

    # Convert blockquotes
    text = re.sub(r"<blockquote[^>]*>", "\n> ", text)
    text = re.sub(r"</blockquote>", "\n", text)

    # Convert horizontal rules
    text = re.sub(r"<hr[^>]*/?>", "\n---\n", text)

    # Remove remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Clean up whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def html_to_markdown(html: str) -> str:
    """Convert HTML content to Markdown.

    Uses html2text if available, falls back to basic converter.

    Args:
        html: HTML string to convert.

    Returns:
        Markdown-formatted string.
    """
    if not html or not html.strip():
        return ""

    try:
        import html2text  # type: ignore[import-not-found]  # noqa: PLC0415

        converter = html2text.HTML2Text()
        converter.ignore_links = False
        converter.ignore_images = False
        converter.body_width = 0
        result: str = converter.handle(html)
        return result.strip()
    except ImportError:
        return _basic_html_to_markdown(html)


def strip_html_tags(html: str) -> str:
    """Strip all HTML tags, returning plain text.

    Args:
        html: HTML string.

    Returns:
        Plain text string.
    """
    if not html or not html.strip():
        return ""
    text = re.sub(r"<[^>]+>", "", html)
    text = html_module.unescape(text)
    return text.strip()


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace: collapse multiple spaces/newlines.

    Args:
        text: Input text.

    Returns:
        Text with normalized whitespace.
    """
    if not text:
        return ""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_markdown(markdown: str) -> str:
    """Normalize Markdown content: fix formatting issues.

    Args:
        markdown: Markdown text.

    Returns:
        Normalized Markdown text.
    """
    if not markdown or not markdown.strip():
        return ""

    text = markdown
    # Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Normalize list markers
    text = re.sub(r"^\s*[-*+]\s+", "- ", text, flags=re.MULTILINE)
    # Fix heading spacing
    text = re.sub(r"^(#{1,6})\s*(.+)$", r"\1 \2", text, flags=re.MULTILINE)
    # Remove trailing whitespace
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    return text.strip()


def normalize_content(content: str, content_type: str = "auto") -> str:
    """Normalize content based on type.

    Detects if HTML and converts to Markdown. Normalizes whitespace.

    Args:
        content: Content string.
        content_type: One of 'auto', 'html', 'markdown', 'plain'.

    Returns:
        Normalized content string.
    """
    if not content or not content.strip():
        return ""

    if content_type == "auto":
        content_type = "html" if "<" in content and ">" in content else "plain"

    if content_type == "html":
        return html_to_markdown(content)
    if content_type == "markdown":
        return normalize_markdown(content)
    return normalize_whitespace(content)
