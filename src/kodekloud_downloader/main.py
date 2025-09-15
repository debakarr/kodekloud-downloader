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
                quiz_markdown.append(f"\n**Explanation**: {question.explanation}")
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
    session = requests.Session()
    session_token = parse_token(cookie)
    headers = {"authorization": f"bearer {session_token}"}
    params = {"course_id": course.id}

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
                url = f"https://learn-api.kodekloud.com/api/courses/{course.id}"
                response = session.get(url, headers=headers, params=params)
                response.raise_for_status()
                course_data = response.json()

                # find the lesson inside course modules
                lesson_data = None
                for module_data in course_data.get("modules", []):
                    for l in module_data.get("lessons", []):
                        if l.get("id") == lesson.id:
                            lesson_data = l
                            break
                    if lesson_data:
                        break

                if not lesson_data:
                    logger.error(f"Lesson {lesson.id} not found in course {course.id}")
                    continue

                lesson_video_url = lesson_data.get("video_url")
                if not lesson_video_url:
                    logger.error(f"No video_url found for lesson {lesson.id} ({lesson.title})")
                    continue

                # Vimeo link
                current_video_url = f"https://player.vimeo.com/video/{lesson_video_url.split('/')[-1]}"

                if (
                    current_video_url in downloaded_videos
                    and downloaded_videos[current_video_url] > max_duplicate_count
                ):
                    raise SystemExit(
                        f"The following video is downloaded more than {max_duplicate_count} times."
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
    except yt_dlp.utils.UnsupportedError:
        logger.error(
            f"Could not download video in link {lesson_video_url}. "
            "Please open link manually and verify that video exists!"
        )
    except yt_dlp.utils.DownloadError as ex:
        logger.error(
            f"Access denied while downloading video or audio file from link {lesson_video_url}\n{ex}"
        )


def download_resource_lesson(lesson_url, file_path: Path, cookie: str) -> None:
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
