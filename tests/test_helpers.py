from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from kodekloud_downloader.helpers import (
    download_all_pdf,
    download_video,
    normalize_name,
    parse_input,
    parse_token,
    sanitize_filename,
)


def test_parse_input_single_number():
    assert parse_input("5") == [5]


def test_parse_input_range():
    assert parse_input("1-4") == [1, 2, 3, 4]


def test_parse_input_combined():
    assert parse_input("1,3-5,8") == [1, 3, 4, 5, 8]


def test_parse_input_invalid_range():
    with pytest.raises(ValueError, match="Invalid range"):
        parse_input("5-2")


def test_sanitize_filename_reserved_windows_chars():
    raw = "File: Name? With * Bad <Chars> and | Slash/Backslash\\"
    cleaned = sanitize_filename(raw)
    for bad_char in '\\/:*?"<>|':
        assert bad_char not in cleaned


def test_sanitize_filename_reserved_device_names():
    for name in ["CON", "prn", "AUX", "NUL", "COM1", "LPT9"]:
        assert sanitize_filename(name) == "_"


def test_sanitize_filename_max_length_and_whitespace():
    raw = "   " + ("a" * 150) + "   "
    cleaned = sanitize_filename(raw, max_length=50)
    assert len(cleaned) <= 50
    assert not cleaned.startswith(" ")
    assert not cleaned.endswith(" ")


def test_normalize_name():
    assert normalize_name("Hello, World! #2026") == "Hello World 2026"


def test_download_all_pdf_handles_tags_without_href(tmp_path: Path):
    """Ensure download_all_pdf doesn't crash with AttributeError on <a> tags lacking href."""
    html = """
    <div>
        <a>Anchor with no href</a>
        <a href="https://example.com/file.pdf">Valid PDF</a>
        <a href="https://example.com/not_a_pdf.html">Not PDF</a>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.content = b"%PDF-1.4 dummy content"
        mock_get.return_value = mock_resp

        # This should NOT raise AttributeError: 'NoneType' object has no attribute 'endswith'
        download_all_pdf(soup, tmp_path, cookie=None)

        assert (tmp_path / "file.pdf").exists()
        assert (tmp_path / "file.pdf").read_bytes() == b"%PDF-1.4 dummy content"


def test_download_video_options_no_conflicting_subtitles():
    """Ensure yt-dlp options don't contain conflicting 'no_write_sub': True when writing subs."""
    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        download_video(
            url="https://player.vimeo.com/video/12345",
            output_path=Path("/tmp/test_video"),
            cookie=None,
            quality="720p",
        )
        assert mock_ydl.called
        opts = mock_ydl.call_args[0][0]
        assert opts.get("writesubtitles") is True
        assert "no_write_sub" not in opts or opts.get("no_write_sub") is not True


def test_parse_token_missing_file():
    with pytest.raises(FileNotFoundError):
        parse_token("non_existent_cookie_file.txt")


def test_download_all_resources_from_markdown(tmp_path: Path):
    """Test extracting and downloading resources (PDF, ZIP, PPTX) from Markdown."""
    from kodekloud_downloader.helpers import download_all_resources

    md_content = """
    # Lecture Notes
    Please download the resources below:
    - [Presentation Deck](https://example.com/slides/chapter1.pdf)
    - [Source Code](https://example.com/code/lab_assets.zip)
    - [PowerPoint Slides](https://example.com/files/lecture.pptx)
    - [External Site](https://example.com/docs)
    """

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_content.return_value = [b"binary_file_content"]
        mock_resp.headers = {"Content-Length": "19"}
        mock_get.return_value = mock_resp

        downloaded = download_all_resources(
            content=md_content,
            download_path=tmp_path,
            session_token="test_token",
        )

        assert len(downloaded) == 3
        assert (tmp_path / "chapter1.pdf").exists()
        assert (tmp_path / "lab_assets.zip").exists()
        assert (tmp_path / "lecture.pptx").exists()
        assert (tmp_path / "chapter1.pdf").read_bytes() == b"binary_file_content"


def test_download_all_resources_handles_query_params_and_skips_existing(tmp_path: Path):
    """Ensure URLs with query params extract clean filenames and existing files are skipped."""
    from kodekloud_downloader.helpers import download_all_resources

    # Pre-create chapter2.pdf to test skip logic
    existing_file = tmp_path / "chapter2.pdf"
    existing_file.write_bytes(b"already_downloaded")

    md_content = """
    [Download](https://res.cloudinary.com/kodekloud/file/upload/v1234/chapter2.pdf?token=xyz&exp=999)
    """

    with patch("requests.get") as mock_get:
        downloaded = download_all_resources(
            content=md_content,
            download_path=tmp_path,
        )

        assert len(downloaded) == 1
        assert existing_file.read_bytes() == b"already_downloaded"
        # requests.get should not have been called because file exists
        assert not mock_get.called


def test_download_all_resources_handles_download_failure_gracefully(tmp_path: Path):
    """Ensure a failed HTTP request logs an error and does not crash."""
    from kodekloud_downloader.helpers import download_all_resources

    md_content = "[Broken Link](https://example.com/missing.pdf)"

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.raise_for_status.side_effect = Exception("404 Not Found")
        mock_get.return_value = mock_resp

        # Should not raise exception
        downloaded = download_all_resources(
            content=md_content,
            download_path=tmp_path,
        )
        assert downloaded == []


def test_normalize_resource_url():
    from kodekloud_downloader.helpers import normalize_resource_url

    # GitHub blob URL converts to raw
    github_blob = "https://github.com/cncf/curriculum/blob/master/PCA_Curriculum.pdf"
    assert (
        normalize_resource_url(github_blob)
        == "https://raw.githubusercontent.com/cncf/curriculum/master/PCA_Curriculum.pdf"
    )

    # Standard URL stays untouched
    std_url = "https://example.com/files/slides.pdf"
    assert normalize_resource_url(std_url) == std_url

    # GitHub raw URL stays untouched
    raw_url = (
        "https://raw.githubusercontent.com/cncf/curriculum/master/PCA_Curriculum.pdf"
    )
    assert normalize_resource_url(raw_url) == raw_url


def test_extract_resource_urls_normalizes_github_blob():
    from kodekloud_downloader.helpers import extract_resource_urls

    md = "[PCA Curriculum](https://github.com/cncf/curriculum/blob/master/PCA_Curriculum.pdf)"
    urls = extract_resource_urls(md)
    assert len(urls) == 1
    assert (
        urls[0][0]
        == "https://raw.githubusercontent.com/cncf/curriculum/master/PCA_Curriculum.pdf"
    )
    assert urls[0][1] == "PCA Curriculum"


def _make_test_course(
    idx: int, title: str, slug: str, tutor_names: list, categories: list
):
    from kodekloud_downloader.models.courses import Category, Course, Tutor

    return Course(
        id=f"id-{idx}",
        slug=slug,
        title=title,
        thumbnail_url="https://example.com/thumb.png",
        tutors=[
            Tutor(
                id=f"t-{name}",
                name=name,
                bio="",
                description="",
                avatar_url="https://example.com/a.png",
            )
            for name in tutor_names
        ],
        popularity=100,
        difficulty_level="Beginner",
        categories=[Category(id=f"c-{c}", name=c) for c in categories],
        plan="Standard",
    )


def test_render_course_table_includes_instructor():
    from kodekloud_downloader.helpers import render_course_table

    c1 = _make_test_course(
        1, "CNPE Prep", "cnpe-prep", ["Nourhan Mohamed"], ["Cloud", "DevOps"]
    )
    table = render_course_table([(1, c1)])
    assert "Instructor" in table.field_names
    assert "Nourhan Mohamed" in str(table)
    assert "CNPE Prep" in str(table)


def test_filter_courses_matches_tutor_title_category():
    from kodekloud_downloader.helpers import _filter_courses

    c1 = _make_test_course(
        1, "CNPE Prep Course", "cnpe", ["Nourhan Mohamed"], ["Cloud"]
    )
    c2 = _make_test_course(
        2, "Docker Absolute", "docker", ["Mumshad Mannambeth"], ["DevOps"]
    )
    courses = [c1, c2]

    # Filter by tutor
    res = _filter_courses(courses, "nourhan")
    assert len(res) == 1
    assert res[0][0] == 1  # 1-based index
    assert res[0][1].title == "CNPE Prep Course"

    # Filter by title / slug
    res = _filter_courses(courses, "docker")
    assert len(res) == 1
    assert res[0][0] == 2

    # Filter by category
    res = _filter_courses(courses, "cloud")
    assert len(res) == 1
    assert res[0][0] == 1

    # No match
    assert _filter_courses(courses, "nonexistent") == []


def test_select_courses_interactive_search():
    from kodekloud_downloader.helpers import select_courses

    c1 = _make_test_course(
        1, "CNPE Prep Course", "cnpe", ["Nourhan Mohamed"], ["Cloud"]
    )
    c2 = _make_test_course(
        2, "Docker Absolute", "docker", ["Mumshad Mannambeth"], ["DevOps"]
    )
    courses = [c1, c2]

    # User searches for 'nourhan', then enters course number '1'
    with patch("builtins.input", side_effect=["nourhan", "1"]):
        selected = select_courses(courses)
        assert len(selected) == 1
        assert selected[0].title == "CNPE Prep Course"

    # User quits immediately
    with patch("builtins.input", side_effect=["q"]):
        selected = select_courses(courses)
        assert selected == []


def test_filter_by_category():
    from kodekloud_downloader.helpers import filter_by_category

    c1 = _make_test_course(
        1, "CKA", "cka", ["Mumshad"], ["Kubernetes", "Golden Kubestronaut"]
    )
    c2 = _make_test_course(2, "KCSA", "kcsa", ["Nourhan"], ["Security"])
    c3 = _make_test_course(3, "Python", "python", ["Sanjeev"], ["Programming"])
    courses = [c1, c2, c3]

    # Single category
    res = filter_by_category(courses, "Security")
    assert len(res) == 1
    assert res[0][1].title == "KCSA"

    # Multi category (comma-separated)
    res = filter_by_category(courses, "Kubernetes, Security")
    assert len(res) == 2

    # Case-insensitive partial matching
    res = filter_by_category(courses, "kubestronaut")
    assert len(res) == 1
    assert res[0][1].title == "CKA"

    # Non-existent category
    res = filter_by_category(courses, "NonExistent")
    assert res == []


def test_render_categories_summary():
    from kodekloud_downloader.helpers import render_categories_summary

    c1 = _make_test_course(1, "CKA", "cka", ["Mumshad"], ["Kubernetes", "DevOps"])
    c2 = _make_test_course(2, "KCSA", "kcsa", ["Nourhan"], ["Security", "Kubernetes"])
    table = render_categories_summary([c1, c2])
    table_str = str(table)
    assert "Kubernetes" in table_str
    assert "DevOps" in table_str
    assert "Security" in table_str


def test_select_courses_category_arg():
    from kodekloud_downloader.helpers import select_courses

    c1 = _make_test_course(1, "CKA", "cka", ["Mumshad"], ["Kubernetes"])
    c2 = _make_test_course(2, "KCSA", "kcsa", ["Nourhan"], ["Security"])
    courses = [c1, c2]

    # Category provided as arg, select course 2
    with patch("builtins.input", side_effect=["2"]):
        selected = select_courses(courses, category="Security")
        assert len(selected) == 1
        assert selected[0].title == "KCSA"


def test_select_courses_interactive_category_command():
    from kodekloud_downloader.helpers import select_courses

    c1 = _make_test_course(1, "CKA", "cka", ["Mumshad"], ["Kubernetes"])
    c2 = _make_test_course(2, "KCSA", "kcsa", ["Nourhan"], ["Security"])
    courses = [c1, c2]

    # Interactive 'c:security' then select 2
    with patch("builtins.input", side_effect=["c:security", "2"]):
        selected = select_courses(courses)
        assert len(selected) == 1
        assert selected[0].title == "KCSA"
