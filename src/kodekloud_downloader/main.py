import logging
from collections import defaultdict
from pathlib import Path
from typing import Union

import markdownify
import requests
import yt_dlp
from bs4 import BeautifulSoup

from kodekloud_downloader.helpers import (
    download_all_pdf,
    download_video,
    is_normal_content,
    normalize_name,
    parse_token,
)
from kodekloud_downloader.models.course import CourseDetail
from kodekloud_downloader.models.courses import Course
from kodekloud_downloader.models.helper import fetch_course_detail
from kodekloud_downloader.models.quiz import Quiz

logger = logging.getLogger(__name__)


def download_quiz(output_dir: str, sep: bool) -> None:
    """
    Download quizzes from the API and save them as Markdown files.

    :param output_dir: The directory path where the Markdown files will be saved.
    :param sep: A boolean flag indicating whether to separate each quiz into individual files.
                 If `True`, each quiz will be saved as a separate Markdown file. If `False`,
                 all quizzes will be combined into a single Markdown file.
    :return: None
    :raises ValueError: If `output_dir` is not a valid directory path.
    :raises requests.RequestException: For errors related to the HTTP request.
    :raises IOError: For file I/O errors.
    """
    quiz_markdown = [] if sep else ["# KodeKloud Quiz"]
    response = requests.get("https://mcq-backend-main.kodekloud.com/api/quizzes/all")
    response.raise_for_status()

    quizzes = [Quiz(**item) for item in response.json()]
    print(f"Total {len(quizzes)} quiz available!")
    for quiz_index, quiz in enumerate(quizzes, start=1):
        quiz_name = quiz.name or quiz.topic
        quiz_markdown.append(f"\n## {quiz_name}")
        print(f"Fetching Quiz {quiz_index} - {quiz_name}")
        questions = quiz.fetch_questions()

        for index, question in enumerate(questions, start=1):
            quiz_markdown.append(f"\n**{index}. {question.question.strip()}**")
            quiz_markdown.append("\n")
            for answer in question.answers:
                quiz_markdown.append(f"* [ ] {answer}")
            quiz_markdown.append(f"\n**Correct answer:**")
            for answer in question.correctAnswers:
                quiz_markdown.append(f"* [x] {answer}")

            if script := question.code.get("script"):
                quiz_markdown.append(f"\n**Code**: \n{script}")
            if question.explanation:
                quiz_markdown.append(f"\n**Explaination**: {question.explanation}")
            if question.documentationLink:
                quiz_markdown.append(
                    f"\n**Documentation Link**: {question.documentationLink}"
                )

        if sep and quiz_name:
            output_file = Path(output_dir) / f"{quiz_name.replace('/', '')}.md"
            markdown_text = "\n".join(quiz_markdown)

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(markdown_text)
            print(f"Quiz file written in {output_file}")

            quiz_markdown = []
        else:
            quiz_markdown.append("\n---\n")

    if not sep:
        output_file = Path(output_dir) / "KodeKloud_Quiz.md"
        markdown_text = "\n".join(quiz_markdown)

        Path(output_file).write_text(markdown_text)
        print(f"Quiz file written in {output_file}")


def parse_course_from_url(url: str) -> CourseDetail:
    """
    Parse the course slug from the given URL and fetch the course details.

    :param url: The URL from which to extract the course slug.
    :return: An instance of `CourseDetail` containing the course details.
    :raises ValueError: If the URL does not contain a valid course slug.
    """
    url = url.strip("/")
    course_slug = url.split("/")[-1]
    return fetch_course_detail(course_slug)


def download_course(
    course: Union[Course, CourseDetail],
    cookie: str,
    quality: str,
    output_dir: Union[str, Path],
    max_duplicate_count: int,
) -> None:
    """
    Download a course from KodeKloud.

    :param course: The Course or CourseDetail object
    :param cookie: The user's authentication cookie
    :param quality: The video quality (e.g. "720p")
    :param output_dir: The output directory for the downloaded course
    :param max_duplicate_count: Maximum duplicate video before after cookie expire message will be raised
    """
    session = requests.Session()
    session_token = parse_token(cookie)
    headers = {"authorization": f"bearer {session_token}"}
    params = {
        "course_id": course.id,
    }

    course_detail = (
        fetch_course_detail(course.slug) if isinstance(course, Course) else course
    )

    downloaded_videos = defaultdict(int)
    for module_index, module in enumerate(course_detail.modules, start=1):
        for lesson_index, lesson in enumerate(module.lessons, start=1):
            file_path = create_file_path(
                output_dir,
                course.title,
                module_index,
                module.title,
                lesson_index,
                lesson.title,
            )

            if lesson.type == "video":
                url = f"https://learn-api.kodekloud.com/api/lessons/{lesson.id}"

                response = session.get(url, headers=headers, params=params)
                response.raise_for_status()
                lesson_video_url = response.json()["video_url"]
                # TODO: Maybe if in future KodeKloud change the video streaming service, this area will need some working.
                # Try to generalize this for future enhacement?
                current_video_url = (
                    f"https://player.vimeo.com/video/{lesson_video_url.split('/')[-1]}"
                )
                if (
                    current_video_url in downloaded_videos
                    and downloaded_videos[current_video_url] > max_duplicate_count
                ):
                    raise SystemExit(
                        f"The folowing video is downloaded more than {max_duplicate_count}."
                        "\nYour cookie might have expired or you don't have access/enrolled to the course."
                        "\nPlease refresh/regenerate the cookie or enroll in the course and try again."
                    )
                download_video_lesson(current_video_url, file_path, cookie, quality)
                downloaded_videos[current_video_url] += 1
            else:
                lesson_url = f"https://learn.kodekloud.com/user/courses/{course.slug}/module/{module.id}/lesson/{lesson.id}"
                download_resource_lesson(lesson_url, file_path, cookie)


def create_file_path(
    output_dir: Union[str, Path],
    course_name: str,
    module_index: int,
    module_name: str,
    lesson_index: int,
    lesson_name: str,
) -> Path:
    """
    Create a file path for a lesson.

    :param output_dir: The output directory for the downloaded course
    :param course_name: The course name
    :param module_index: The module index
    :param item_name: The module name
    :param lesson_index: The lesson index
    :param lesson_name: The lesson name
    :return: The created file path
    """
    return Path(
        Path(output_dir)
        / "KodeKloud"
        / normalize_name(course_name)
        / f"{module_index} - {normalize_name(module_name)}"
        / f"{lesson_index} - {normalize_name(lesson_name)}"
    )


def download_video_lesson(
    lesson_video_url, file_path: Path, cookie: str, quality: str
) -> None:
    """
    Download a video lesson.

    :param lesson_video_url: The lesson video URL
    :param file_path: The output file path for the video
    :param cookie: The user's authentication cookie
    :param quality: The video quality (e.g. "720p")
    """
    logger.info(f"Writing video file... {file_path}...")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Parsing url: {lesson_video_url}")
    try:
        download_video(
            url=lesson_video_url,
            output_path=file_path,
            cookie=cookie,
            quality=quality,
        )
    except yt_dlp.utils.UnsupportedError as ex:
        logger.error(
            f"Could not download video in link {lesson_video_url}. "
            "Please open link manually and verify that video exists!"
        )
    except yt_dlp.utils.DownloadError as ex:
        logger.error(
            f"Access denied while downloading video or audio file from link {lesson_video_url}\n{ex}"
        )


def download_resource_lesson(lesson_url, file_path: Path, cookie: str) -> None:
    """
    Download a resource lesson.

    :param lesson_url: The lesson url
    :param file_path: The output file path for the resource
    :param cookie: The user's authentication cookie
    """
    # TODO: Did we break this? I have no idea.
    page = requests.get(lesson_url)
    soup = BeautifulSoup(page.content, "html.parser")
    content = soup.find("div", class_="learndash_content_wrap")

    if content and is_normal_content(content):
        logger.info(f"Writing resource file... {file_path}...")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.with_suffix(".md").write_text(
            markdownify.markdownify(content.prettify()), encoding="utf-8"
        )
        download_all_pdf(content=content, download_path=file_path.parent, cookie=cookie)
