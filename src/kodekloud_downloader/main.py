import logging
from pathlib import Path
from typing import Union

import markdownify
import requests
from bs4 import BeautifulSoup

from kodekloud_downloader.helpers import (
    download_all_pdf,
    download_video,
    get_video_info,
    is_normal_content,
    normalize_name,
)
from kodekloud_downloader.models import Topic

import yt_dlp  # isort: skip


logger = logging.getLogger(__name__)


def download_course(url: str, cookie: str, quality: str, output_dir: Union[str, Path]) -> None:
    """
    Download a course from KodeKloud.

    :param url: The course URL
    :param cookie: The user's authentication cookie
    :param quality: The video quality (e.g. "720p")
    :param output_dir: The output directory for the downloaded course
    """
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    course_name_tag = soup.find("h1", class_="course_title") or soup.find("h1", class_="entry-title")
    course_name = course_name_tag.text.strip()
    main_lesson_content = soup.find("div", class_="lessons_main__content") or soup.find("div", class_="ld-lesson-list")
    topics = main_lesson_content.find_all("div", class_="w-dyn-item") or main_lesson_content.find_all(
        "div", class_="ld-item-list-items"
    )
    items = [Topic.make(topic) for topic in topics]

    video_infos = set()
    for i, item in enumerate(items, start=1):
        for j, lesson in enumerate(item.lessons, start=1):
            file_path = create_file_path(output_dir, course_name, i, item.name, j, lesson.name)

            if lesson.is_video:
                video_info = get_video_info(lesson.url, cookie=cookie).get("url")
                if video_info in video_infos:
                    raise SystemExit(
                        "Your cookie might have expired or you don't have access to the course."
                        "\nPlease refresh/regenerate the cookie or enroll in the course and try again."
                    )
                download_video_lesson(lesson, file_path, cookie, quality)
                video_infos.add(video_info)
            else:
                download_resource_lesson(lesson, file_path, cookie)


def create_file_path(
    output_dir: Union[str, Path],
    course_name: str,
    i: int,
    item_name: str,
    j: int,
    lesson_name: str,
) -> Path:
    """
    Create a file path for a lesson.

    :param output_dir: The output directory for the downloaded course
    :param course_name: The course name
    :param i: The topic index
    :param item_name: The topic name
    :param j: The lesson index
    :param lesson_name: The lesson name
    :return: The created file path
    """
    return Path(
        Path(output_dir)
        / "KodeKloud"
        / normalize_name(course_name)
        / f"{i} - {normalize_name(item_name)}"
        / f"{j} - {normalize_name(lesson_name)}"
    )


def download_video_lesson(lesson, file_path: Path, cookie: str, quality: str) -> None:
    """
    Download a video lesson.

    :param lesson: The lesson object
    :param file_path: The output file path for the video
    :param cookie: The user's authentication cookie
    :param quality: The video quality (e.g. "720p")
    """
    logger.info(f"Writing video file... {file_path}...")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Parsing url: {lesson.url}")
    try:
        download_video(
            url=lesson.url,
            output_path=file_path,
            cookie=cookie,
            quality=quality,
        )
    except yt_dlp.utils.UnsupportedError as ex:
        logger.error(
            f"Could not download video in link {lesson.url}. " "Please open link manually and verify that video exists!"
        )
    except yt_dlp.utils.DownloadError as ex:
        logger.error(f"Access denied while downloading video or audio file from link {lesson.url}")


def download_resource_lesson(lesson, file_path: Path, cookie: str) -> None:
    """
    Download a resource lesson.

    :param lesson: The lesson object
    :param file_path: The output file path for the resource
    :param cookie: The user's authentication cookie
    """
    page = requests.get(lesson.url)
    soup = BeautifulSoup(page.content, "html.parser")
    content = soup.find("div", class_="learndash_content_wrap")

    if content and is_normal_content(content):
        logger.info(f"Writing resource file... {file_path}...")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.with_suffix(".md").write_text(markdownify.markdownify(content.prettify()), encoding="utf-8")
        download_all_pdf(content=content, download_path=file_path.parent, cookie=cookie)
