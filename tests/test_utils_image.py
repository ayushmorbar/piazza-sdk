"""Tests for piazza_sdk.utils.image."""

from __future__ import annotations

from piazza_sdk.utils.image import (
    detect_image_type,
    get_mime_type,
    is_image_url,
    normalize_image_url,
)


class TestIsImageUrl:
    """Tests for is_image_url."""

    def test_empty_string(self):
        assert is_image_url("") is False

    def test_whitespace_only(self):
        assert is_image_url("   ") is False

    def test_jpg_extension(self):
        assert is_image_url("https://example.com/photo.jpg") is True

    def test_jpeg_extension(self):
        assert is_image_url("https://example.com/photo.jpeg") is True

    def test_png_extension(self):
        assert is_image_url("https://example.com/photo.png") is True

    def test_gif_extension(self):
        assert is_image_url("https://example.com/photo.gif") is True

    def test_webp_extension(self):
        assert is_image_url("https://example.com/photo.webp") is True

    def test_svg_extension(self):
        assert is_image_url("https://example.com/icon.svg") is True

    def test_bmp_extension(self):
        assert is_image_url("https://example.com/photo.bmp") is True

    def test_ico_extension(self):
        assert is_image_url("https://example.com/favicon.ico") is True

    def test_uppercase_extension(self):
        assert is_image_url("https://example.com/photo.PNG") is True

    def test_mixed_case_extension(self):
        assert is_image_url("https://example.com/photo.JpEg") is True

    def test_txt_extension(self):
        assert is_image_url("https://example.com/file.txt") is False

    def test_html_extension(self):
        assert is_image_url("https://example.com/page.html") is False

    def test_no_extension(self):
        assert is_image_url("https://example.com/photo") is False

    def test_query_params_after_extension(self):
        assert is_image_url("https://example.com/photo.png?width=100") is True

    def test_fragment_after_extension(self):
        assert is_image_url("https://example.com/photo.jpg#section") is True

    def test_trailing_slash(self):
        assert is_image_url("https://example.com/photo.png/") is False

    def test_image_in_middle_of_path(self):
        assert is_image_url("https://example.com/images/photo.png") is True

    def test_relative_path_with_extension(self):
        assert is_image_url("/static/img/photo.gif") is True

    def test_just_extension(self):
        assert is_image_url(".png") is True

    def test_path_with_dots_in_name(self):
        assert is_image_url("https://example.com/my.photo.v2.png") is True

    def test_unsupported_extension(self):
        assert is_image_url("https://example.com/file.tiff") is False

    def test_pdf_extension(self):
        assert is_image_url("https://example.com/doc.pdf") is False

    def test_long_path_with_image_extension(self):
        url = "https://cdn.example.com/assets/images/2025/01/photo.jpg"
        assert is_image_url(url) is True

    def test_non_string_like_input(self):
        assert is_image_url(None) is False  # type: ignore[arg-type]


class TestGetMimeType:
    """Tests for get_mime_type."""

    def test_empty_string(self):
        assert get_mime_type("") is None

    def test_jpg(self):
        assert get_mime_type("https://example.com/photo.jpg") == "image/jpeg"

    def test_jpeg(self):
        assert get_mime_type("https://example.com/photo.jpeg") == "image/jpeg"

    def test_png(self):
        assert get_mime_type("https://example.com/photo.png") == "image/png"

    def test_gif(self):
        assert get_mime_type("https://example.com/photo.gif") == "image/gif"

    def test_webp(self):
        assert get_mime_type("https://example.com/photo.webp") == "image/webp"

    def test_svg(self):
        assert get_mime_type("https://example.com/icon.svg") == "image/svg+xml"

    def test_bmp(self):
        assert get_mime_type("https://example.com/photo.bmp") == "image/bmp"

    def test_ico(self):
        assert get_mime_type("https://example.com/favicon.ico") == "image/x-icon"

    def test_uppercase_extension(self):
        assert get_mime_type("https://example.com/photo.PNG") == "image/png"

    def test_mixed_case(self):
        assert get_mime_type("https://example.com/photo.JpEg") == "image/jpeg"

    def test_unknown_extension(self):
        assert get_mime_type("https://example.com/file.tiff") is None

    def test_no_extension(self):
        assert get_mime_type("https://example.com/photo") is None

    def test_relative_path(self):
        assert get_mime_type("/static/img/logo.svg") == "image/svg+xml"

    def test_query_params_after_extension(self):
        assert get_mime_type("https://example.com/photo.png?w=100") == "image/png"

    def test_fragment_after_extension(self):
        assert get_mime_type("https://example.com/photo.jpg#thumb") == "image/jpeg"

    def test_whitespace_url(self):
        assert get_mime_type("   ") is None

    def test_non_string_like_input(self):
        assert get_mime_type(None) is None  # type: ignore[arg-type]


class TestDetectImageType:
    """Tests for detect_image_type."""

    def test_empty_bytes(self):
        assert detect_image_type(b"") is None

    def test_short_data(self):
        assert detect_image_type(b"\x89PN") is None

    def test_single_byte(self):
        assert detect_image_type(b"\x89") is None

    def test_three_bytes(self):
        assert detect_image_type(b"\x89PNG") is None

    def test_png_magic(self):
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
        assert detect_image_type(data) == "image/png"

    def test_jpeg_magic(self):
        data = b"\xff\xd8\xff\xe0" + b"\x00" * 20
        assert detect_image_type(data) == "image/jpeg"

    def test_gif87a_magic(self):
        data = b"GIF87a" + b"\x00" * 20
        assert detect_image_type(data) == "image/gif"

    def test_gif89a_magic(self):
        data = b"GIF89a" + b"\x00" * 20
        assert detect_image_type(data) == "image/gif"

    def test_webp_magic(self):
        data = b"RIFF" + b"\x00" * 4 + b"WEBP" + b"\x00" * 20
        assert detect_image_type(data) == "image/webp"

    def test_svg_xml_declaration(self):
        data = b'<?xml version="1.0"?>\n<svg>content</svg>'
        assert detect_image_type(data) == "image/svg+xml"

    def test_svg_tag_start(self):
        data = b'<svg xmlns="http://www.w3.org/2000/svg">content</svg>'
        assert detect_image_type(data) == "image/svg+xml"

    def test_svg_uppercase(self):
        data = b'<SVG xmlns="http://www.w3.org/2000/svg">'
        assert detect_image_type(data) == "image/svg+xml"

    def test_unrecognized_data(self):
        data = b"\x00\x00\x00\x00" + b"\xff" * 10
        assert detect_image_type(data) is None

    def test_random_bytes(self):
        data = bytes(range(256))
        assert detect_image_type(data) is None

    def test_png_only_header(self):
        data = b"\x89PNG\r\n\x1a\n"
        assert detect_image_type(data) == "image/png"

    def test_jpeg_only_header(self):
        data = b"\xff\xd8"
        assert detect_image_type(data) is None

    def test_webp_riiff_without_webp_tag(self):
        data = b"RIFF" + b"\x00" * 4 + b"NOTW" + b"\x00" * 20
        assert detect_image_type(data) is None

    def test_webp_riiff_short(self):
        data = b"RIFF" + b"\x00" * 4 + b"WEB"
        assert detect_image_type(data) is None

    def test_svg_self_closing_tag(self):
        data = b"<svg/>"
        assert detect_image_type(data) == "image/svg+xml"

    def test_real_png_header(self):
        data = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR"
            + b"\x00" * 20
        )
        assert detect_image_type(data) == "image/png"

    def test_real_jpeg_header(self):
        data = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 20
        assert detect_image_type(data) == "image/jpeg"


class TestNormalizeImageUrl:
    """Tests for normalize_image_url."""

    def test_empty_string(self):
        assert normalize_image_url("") == ""

    def test_whitespace_only(self):
        assert normalize_image_url("   ") == ""

    def test_absolute_https(self):
        url = "https://example.com/photo.png"
        assert normalize_image_url(url) == url

    def test_absolute_http(self):
        url = "http://example.com/photo.png"
        assert normalize_image_url(url) == url

    def test_relative_root_path(self):
        result = normalize_image_url("/static/img/photo.png", "https://piazza.com")
        assert result == "https://piazza.com/static/img/photo.png"

    def test_relative_root_path_no_base(self):
        result = normalize_image_url("/static/img/photo.png")
        assert result == "/static/img/photo.png"

    def test_relative_root_path_with_path_in_base(self):
        result = normalize_image_url("/img/photo.png", "https://piazza.com/class/math")
        assert result == "https://piazza.com/img/photo.png"

    def test_absolute_preserves_query(self):
        url = "https://example.com/photo.png?width=100&height=200"
        assert normalize_image_url(url) == url

    def test_absolute_preserves_fragment(self):
        url = "https://example.com/photo.png#thumb"
        assert normalize_image_url(url) == url

    def test_strips_leading_whitespace(self):
        result = normalize_image_url("  https://example.com/photo.png")
        assert result == "https://example.com/photo.png"

    def test_strips_trailing_whitespace(self):
        result = normalize_image_url("https://example.com/photo.png  ")
        assert result == "https://example.com/photo.png"

    def test_strips_both_whitespace(self):
        result = normalize_image_url("  https://example.com/photo.png  ")
        assert result == "https://example.com/photo.png"

    def test_relative_without_leading_slash(self):
        result = normalize_image_url("photo.png", "https://piazza.com")
        assert result == "photo.png"

    def test_base_url_with_port(self):
        result = normalize_image_url("/img/photo.png", "https://piazza.com:8080")
        assert result == "https://piazza.com:8080/img/photo.png"

    def test_base_url_with_path(self):
        result = normalize_image_url("/img/photo.png", "https://piazza.com/class/CS101")
        assert result == "https://piazza.com/img/photo.png"

    def test_absolute_url_with_base_ignored(self):
        url = "https://other.com/photo.png"
        result = normalize_image_url(url, "https://piazza.com")
        assert result == "https://other.com/photo.png"

    def test_non_string_like_url(self):
        assert normalize_image_url(None) == ""  # type: ignore[arg-type]

    def test_relative_root_deep_path(self):
        result = normalize_image_url("/a/b/c/d.png", "https://cdn.example.com")
        assert result == "https://cdn.example.com/a/b/c/d.png"

    def test_relative_without_slash(self):
        result = normalize_image_url("images/photo.png", "https://piazza.com")
        assert result == "images/photo.png"
