import logging
from pathlib import Path
from typing import Union

import markdownify
import requests
from bs4 import BeautifulSoup

from kodekloud_downloader.helpers import download_all_pdf, download_video, is_normal_content, normalize_name
from kodekloud_downloader.models import Topic

logger = logging.getLogger(__name__)


def download_course(url: str, cookie: str, quality: str, output_dir: Union[str, Path]) -> None:
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    course_name = soup.find("h1", class_="course_title").text.strip()
    main_lesson_content = soup.find("div", class_="lessons_main__content")
    topics = main_lesson_content.find_all("div", class_="w-dyn-item")
    items = []
    for topic in topics:
        items.append(Topic.make(topic))
    for i, item in enumerate(items, start=1):
        for j, lesson in enumerate(item.lessons, start=1):
            file_path = Path(
                Path(output_dir)
                / "KodeKloud"
                / normalize_name(course_name)
                / f"{i} - {normalize_name(item.name)}"
                / f"{j} - {normalize_name(lesson.name)}"
            )
            if lesson.is_video:
                logger.info(f"Writing video file... {file_path}...")
                file_path.parent.mkdir(parents=True, exist_ok=True)
                logger.info(f"Parsing url: {lesson.url}")
                download_video(url=lesson.url, output_path=file_path, cookie=cookie, quality=quality)
            else:
                page = requests.get(lesson.url)
                soup = BeautifulSoup(page.content, "html.parser")
                content = soup.find("div", class_="learndash_content_wrap")
                # TODO: Fix this part. Most probably resources are not getting downloaded
                if content and is_normal_content(content):
                    logger.info(f"Writing resource file... {file_path}...")
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.with_suffix(".md").write_text(
                        markdownify.markdownify(content.prettify()), encoding="utf-8"
                    )
                    download_all_pdf(content=content, download_path=file_path.parent, cookie=cookie)
