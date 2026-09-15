from kodekloud_downloader.main import (
    _MAX_PATH_LENGTH,
    _shorten_component,
    create_file_path,
)


def test_shorten_component_short_string():
    assert _shorten_component("hello", 10) == "hello"


def test_shorten_component_no_extension():
    assert _shorten_component("very_long_component_name", 10) == "very_long_"


def test_shorten_component_preserves_extension():
    res = _shorten_component("long_document_title.pdf", 15)
    assert res.endswith(".pdf")
    assert len(res) <= 15


def test_create_file_path_under_max_length():
    path = create_file_path(
        output_dir="/tmp/downloads",
        course_name="Docker Basics",
        module_index=1,
        module_name="Getting Started",
        lesson_index=2,
        lesson_name="Containers",
    )
    assert len(str(path)) <= _MAX_PATH_LENGTH
    assert "Docker Basics" in str(path)
    assert "Getting Started" in str(path)
    assert "002 - Containers" in str(path)


def test_create_file_path_zero_pads_lesson_index():
    path = create_file_path(
        output_dir="/tmp/downloads",
        course_name="Kubernetes",
        module_index=1,
        module_name="Intro",
        lesson_index=7,
        lesson_name="Pods",
    )
    assert "007 - Pods" in str(path)


def test_create_file_path_zero_pads_module_index():
    path = create_file_path(
        output_dir="/tmp/downloads",
        course_name="Kubernetes",
        module_index=3,
        module_name="Networking",
        lesson_index=5,
        lesson_name="Services",
    )
    assert "03 - Networking" in str(path)


def test_create_file_path_truncates_overly_long_path():
    long_course = "A" * 100
    long_module = "B" * 100
    long_lesson = "C" * 100
    path = create_file_path(
        output_dir="/tmp/downloads",
        course_name=long_course,
        module_index=1,
        module_name=long_module,
        lesson_index=1,
        lesson_name=long_lesson,
    )
    assert len(str(path)) <= _MAX_PATH_LENGTH


def test_create_file_path_preserves_extension_when_shortening():
    long_base = "/tmp/" + ("X" * 150)
    path = create_file_path(
        output_dir=long_base,
        course_name="Course A",
        module_index=1,
        module_name="Module B",
        lesson_index=1,
        lesson_name=("Lesson C " * 4) + ".vtt",
    )
    assert len(str(path)) <= _MAX_PATH_LENGTH
    assert str(path).endswith(".vtt")


def test_download_course_handles_401_gracefully():
    from unittest.mock import MagicMock, patch

    import pytest
    import requests

    from kodekloud_downloader.main import download_course

    mock_course = MagicMock()
    mock_course.id = "test-course-id"
    mock_module = MagicMock()
    mock_module.id = "mod-1"
    mock_module.title = "Module 1"
    mock_lesson = MagicMock()
    mock_lesson.id = "lesson-1"
    mock_lesson.title = "Lesson 1"
    mock_lesson.type = "video"
    mock_module.lessons = [mock_lesson]
    mock_course.modules = [mock_module]

    with patch("requests.Session") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        mock_resp = MagicMock()
        mock_resp.status_code = 401
        http_err = requests.exceptions.HTTPError(
            "401 Client Error: Unauthorized", response=mock_resp
        )
        mock_resp.raise_for_status.side_effect = http_err
        mock_session.get.return_value = mock_resp

        with pytest.raises(SystemExit) as exc_info:
            download_course(
                course=mock_course,
                quality="720p",
                output_dir="/tmp/test",
                max_duplicate_count=3,
                session_token="invalid_token",
            )
        assert "401" in str(exc_info.value) or "expired" in str(exc_info.value).lower()


def test_download_resource_lesson_api_writes_markdown_and_downloads_resources(tmp_path):
    from unittest.mock import MagicMock, patch

    from kodekloud_downloader.main import download_resource_lesson

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "lesson-art-1",
        "title": "Course Slides",
        "type": "article",
        "content": "# Slides\nDownload: [Slides](https://example.com/slides.pdf)",
    }

    file_path = tmp_path / "01 - Intro" / "01 - Slides"

    with patch("requests.get", return_value=mock_resp) as mock_get, patch(
        "kodekloud_downloader.main.download_all_resources"
    ) as mock_dl_res:
        download_resource_lesson(
            lesson_url="https://learn.kodekloud.com/user/courses/test-slug/module/m1/lesson/lesson-art-1",
            file_path=file_path,
            cookie=None,
            session_token="valid_jwt",
            lesson_id="lesson-art-1",
            course_id="course-123",
        )

        assert mock_get.called
        assert (file_path.with_suffix(".md")).exists()
        assert "# Slides" in (file_path.with_suffix(".md")).read_text(encoding="utf-8")
        assert mock_dl_res.called
        # download_all_resources should receive the content and destination directory
        kwargs = mock_dl_res.call_args.kwargs
        args = mock_dl_res.call_args.args
        actual_content = kwargs.get("content") or (args[0] if args else None)
        actual_dest = kwargs.get("download_path") or (
            args[1] if len(args) > 1 else None
        )
        assert actual_content == mock_resp.json.return_value["content"]
        assert actual_dest == file_path.parent


def test_download_course_handles_article_lessons(tmp_path):
    from unittest.mock import MagicMock, patch

    from kodekloud_downloader.main import download_course

    mock_course = MagicMock()
    mock_course.id = "c-1"
    mock_course.slug = "c-slug"
    mock_course.title = "Sample Course"

    mock_module = MagicMock()
    mock_module.id = "m-1"
    mock_module.title = "Module One"

    mock_lesson = MagicMock()
    mock_lesson.id = "l-1"
    mock_lesson.title = "Course Deck"
    mock_lesson.type = "article"

    mock_module.lessons = [mock_lesson]
    mock_course.modules = [mock_module]

    with patch("requests.Session") as mock_session_cls, patch(
        "kodekloud_downloader.main.download_resource_lesson"
    ) as mock_dl_res_lesson:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        download_course(
            course=mock_course,
            quality="720p",
            output_dir=tmp_path,
            max_duplicate_count=3,
            session_token="valid_jwt",
        )

        assert mock_dl_res_lesson.called
        assert mock_dl_res_lesson.call_args[1].get(
            "lesson_id"
        ) == "l-1" or mock_dl_res_lesson.call_args[0][0].endswith("l-1")


def test_download_course_global_sequential_indexing(tmp_path):
    from unittest.mock import MagicMock, patch

    from kodekloud_downloader.main import download_course

    mock_course = MagicMock()
    mock_course.id = "c-1"
    mock_course.slug = "c-slug"
    mock_course.title = "Sample Course"

    # Module 1 with 2 lessons
    m1 = MagicMock()
    m1.id = "m-1"
    m1.title = "Module 1"
    l1 = MagicMock(id="l-1", title="Lesson 1", type="article")
    l2 = MagicMock(id="l-2", title="Lesson 2", type="article")
    m1.lessons = [l1, l2]

    # Module 2 with 2 lessons
    m2 = MagicMock()
    m2.id = "m-2"
    m2.title = "Module 2"
    l3 = MagicMock(id="l-3", title="Lesson 3", type="article")
    l4 = MagicMock(id="l-4", title="Lesson 4", type="article")
    m2.lessons = [l3, l4]

    mock_course.modules = [m1, m2]

    captured_file_paths = []

    def fake_download_resource(lesson_url, file_path, *args, **kwargs):
        captured_file_paths.append(str(file_path))

    with patch("requests.Session"), patch(
        "kodekloud_downloader.main.download_resource_lesson",
        side_effect=fake_download_resource,
    ):
        download_course(
            course=mock_course,
            quality="720p",
            output_dir=tmp_path,
            max_duplicate_count=3,
            session_token="valid_jwt",
        )

    assert len(captured_file_paths) == 4
    # Check that lesson indexing increments across modules
    assert "001 - Lesson 1" in captured_file_paths[0]
    assert "002 - Lesson 2" in captured_file_paths[1]
    assert "003 - Lesson 3" in captured_file_paths[2]
    assert "004 - Lesson 4" in captured_file_paths[3]
