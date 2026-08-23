"""Tests for piazza_sdk.utils."""

from __future__ import annotations

from piazza_sdk.utils.normalization import (
    html_to_markdown,
    normalize_content,
    normalize_markdown,
    normalize_whitespace,
    strip_html_tags,
)


class TestHtmlToMarkdown:
    """Tests for HTML to Markdown conversion."""

    def test_empty_string(self):
        assert html_to_markdown("") == ""

    def test_none_like_empty(self):
        assert html_to_markdown("   ") == ""

    def test_paragraph(self):
        result = html_to_markdown("<p>Hello world</p>")
        assert "Hello world" in result

    def test_bold(self):
        result = html_to_markdown("<strong>bold</strong>")
        assert "**bold**" in result

    def test_italic(self):
        result = html_to_markdown("<em>italic</em>")
        assert "*italic*" in result

    def test_code(self):
        result = html_to_markdown("<code>x = 1</code>")
        assert "`x = 1`" in result

    def test_heading(self):
        result = html_to_markdown("<h1>Title</h1>")
        assert "# Title" in result

    def test_link(self):
        result = html_to_markdown('<a href="https://example.com">click</a>')
        assert "[click](https://example.com)" in result

    def test_image(self):
        result = html_to_markdown('<img src="https://example.com/img.png" />')
        assert "![image](https://example.com/img.png)" in result

    def test_nested_tags(self):
        html = "<p>This is <strong>bold</strong> and <em>italic</em> text.</p>"
        result = html_to_markdown(html)
        assert "bold" in result
        assert "italic" in result

    def test_html_entities(self):
        result = html_to_markdown("5 &gt; 3 &amp; 2 &lt; 4")
        assert "5 > 3 & 2 < 4" in result

    def test_br_tag(self):
        result = html_to_markdown("line1<br>line2")
        assert "\n" in result
        assert "line1" in result
        assert "line2" in result

    def test_list_items(self):
        result = html_to_markdown("<ul><li>one</li><li>two</li></ul>")
        assert "- one" in result
        assert "- two" in result


class TestStripHtmlTags:
    """Tests for HTML tag stripping."""

    def test_empty(self):
        assert strip_html_tags("") == ""

    def test_strips_tags(self):
        assert strip_html_tags("<p>Hello</p>") == "Hello"

    def test_entities_unescaped(self):
        assert strip_html_tags("a &amp; b") == "a & b"


class TestNormalizeWhitespace:
    """Tests for whitespace normalization."""

    def test_empty(self):
        assert normalize_whitespace("") == ""

    def test_collapses_spaces(self):
        assert normalize_whitespace("a   b") == "a b"

    def test_collapses_newlines(self):
        result = normalize_whitespace("a\n\n\n\n\nb")
        assert result == "a\n\nb"

    def test_strips_leading_trailing(self):
        assert normalize_whitespace("  hello  ") == "hello"


class TestNormalizeContent:
    """Tests for content normalization with type detection."""

    def test_empty(self):
        assert normalize_content("") == ""

    def test_auto_html(self):
        result = normalize_content("<p>Hello</p>", "auto")
        assert "Hello" in result

    def test_auto_plain(self):
        result = normalize_content("Hello world", "auto")
        assert result == "Hello world"

    def test_explicit_html(self):
        result = normalize_content("<strong>hi</strong>", "html")
        assert "**hi**" in result

    def test_explicit_markdown(self):
        result = normalize_content("**bold**", "markdown")
        assert "**bold**" in result

    def test_explicit_plain(self):
        result = normalize_content("  spaces  ", "plain")
        assert result == "spaces"


class TestNormalizeMarkdown:
    """Tests for normalize_markdown function."""

    def test_normalize_markdown_empty_string(self):
        assert normalize_markdown("") == ""

    def test_normalize_markdown_whitespace_only(self):
        assert normalize_markdown("   ") == ""

    def test_normalize_markdown_list_marker_star(self):
        result = normalize_markdown("* item")
        assert result == "- item"

    def test_normalize_markdown_list_marker_plus(self):
        result = normalize_markdown("+ item")
        assert result == "- item"

    def test_normalize_markdown_list_marker_dash(self):
        result = normalize_markdown("- item")
        assert result == "- item"

    def test_normalize_markdown_list_marker_indented(self):
        result = normalize_markdown("  * item")
        assert result == "- item"

    def test_normalize_markdown_list_multiple_items(self):
        input_md = "* first\n+ second\n- third"
        result = normalize_markdown(input_md)
        assert result == "- first\n- second\n- third"

    def test_normalize_markdown_heading_single_space(self):
        result = normalize_markdown("## Title")
        assert result == "## Title"

    def test_normalize_markdown_heading_missing_space(self):
        result = normalize_markdown("##Title")
        assert result == "## Title"

    def test_normalize_markdown_heading_all_levels(self):
        input_md = "#H1\n##H2\n###H3\n####H4\n#####H5\n######H6"
        result = normalize_markdown(input_md)
        assert result == "# H1\n## H2\n### H3\n#### H4\n##### H5\n###### H6"

    def test_normalize_markdown_heading_extraspace(self):
        result = normalize_markdown("##  Title")
        assert result == "## Title"

    def test_normalize_markdown_trailing_whitespace(self):
        result = normalize_markdown("line   \nmore   ")
        assert result == "line\nmore"

    def test_normalize_markdown_blank_line_collapse(self):
        input_md = "a\n\n\n\nb"
        result = normalize_markdown(input_md)
        assert result == "a\n\nb"

    def test_normalize_markdown_blank_line_three(self):
        input_md = "a\n\n\nb"
        result = normalize_markdown(input_md)
        assert result == "a\n\nb"

    def test_normalize_markdown_blank_line_two_unchanged(self):
        input_md = "a\n\nb"
        result = normalize_markdown(input_md)
        assert result == "a\n\nb"

    def test_normalize_markdown_already_clean(self):
        input_md = "Heading\n\nSome text\n\nAnother paragraph"
        result = normalize_markdown(input_md)
        assert result == "Heading\n\nSome text\n\nAnother paragraph"

    def test_normalize_markdown_mixed_content(self):
        input_md = "# Heading\n\n* item1\n+ item2\n- item3\n\n##Subheading\n\nText here   "
        result = normalize_markdown(input_md)
        expected = "# Heading\n- item1\n- item2\n- item3\n\n## Subheading\n\nText here"
        assert result == expected

    def test_normalize_markdown_strip_leading_trailing(self):
        result = normalize_markdown("\n\nHello\n\n")
        assert result == "Hello"

    def test_normalize_markdown_code_block_unchanged(self):
        input_md = "```\ncode here\n```"
        result = normalize_markdown(input_md)
        assert result == "```\ncode here\n```"

    def test_normalize_markdown_list_with_heading(self):
        input_md = "* Item one\n##Section\n+ Item two"
        result = normalize_markdown(input_md)
        assert result == "- Item one\n## Section\n- Item two"
