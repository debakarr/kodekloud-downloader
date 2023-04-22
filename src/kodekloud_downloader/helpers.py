import logging
import string
from pathlib import Path
from typing import List

import prettytable
import requests
import yt_dlp

from kodekloud_downloader.models import Course

logger = logging.getLogger(__name__)


def select_course(courses: List[Course]) -> Course:
    table = prettytable.PrettyTable()
    table.field_names = ["No.", "Name", "Type", "Categories"]

    for i, course in enumerate(courses):
        table.add_row([i + 1, course.name, course.course_type, ", ".join(course.categories)])

    table.align["No."] = "l"
    table.align["Name"] = "l"
    table.align["Type"] = "l"
    table.align["Categories"] = "l"

    print(table)

    selected_course = input("Enter the number of the course you want to select: ")
    course = courses[int(selected_course) - 1]

    return course


def normalize_name(name: str) -> str:
    return name.translate(str.maketrans("", "", string.punctuation))


def download_video(url: str, output_path: Path, cookie: str, quality: str) -> int:
    ydl_opts = {
        "format": f"bestvideo[height<={quality[:-1]}]+bestaudio/best[height<={quality[:-1]}]/best",
        "concurrent_fragment_downloads": 15,
        "outtmpl": f"{output_path}.%(ext)s",
        "verbose": logger.getEffectiveLevel() == logging.DEBUG,
        "cookiefile": cookie,
        "merge_output_format": "mkv",
    }
    logger.debug(f"Calling download with following options: {ydl_opts}")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download(url)


def normalize_name(name: str) -> str:
    return name.translate(str.maketrans("", "", string.punctuation))


def is_normal_content(content: str) -> bool:
    is_lab = content.find("div", class_="start-lab-button")
    is_feedback = content.find_all("iframe")
    return not (is_lab or is_feedback)


def download_all_pdf(content, download_path: Path, cookie: str) -> None:
    for link in content.find_all("a"):
        href = link.get("href")
        if href.endswith("pdf"):
            file_name = download_path / Path(href).name
            print(f"Downloading {file_name}...")
            response = requests.get(href, headers={"Cookie": cookie})
            file_name.write_bytes(response.content)
