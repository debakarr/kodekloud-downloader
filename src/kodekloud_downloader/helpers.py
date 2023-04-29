import hashlib
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
    """
    Display a table of courses and ask the user to select one by entering its number.

    :param courses: A list of Course objects to choose from
    :return: The selected Course object
    """
    table = prettytable.PrettyTable()
    table.field_names = ["No.", "Name", "Type", "Categories"]

    for i, course in enumerate(courses):
        table.add_row(
            [i + 1, course.name, course.course_type, ", ".join(course.categories)]
        )

    table.align["No."] = "l"
    table.align["Name"] = "l"
    table.align["Type"] = "l"
    table.align["Categories"] = "l"

    print(table)

    selected_course = input("Enter the number of the course you want to select: ")
    course = courses[int(selected_course) - 1]

    return course


def normalize_name(name: str) -> str:
    """
    Remove punctuation from a string.

    :param name: The input string
    :return: The string without punctuation
    """
    return name.translate(str.maketrans("", "", string.punctuation))


def download_video(url: str, output_path: Path, cookie: str, quality: str) -> None:
    """
    Download a video using yt_dlp with the given options.

    :param url: The video URL
    :param output_path: The output directory for the downloaded video
    :param cookie: The user's authentication cookie
    :param quality: The video quality (e.g. "720p")
    """
    ydl_opts = {
        "format": f"bestvideo[height<={quality[:-1]}]+bestaudio/best[height<={quality[:-1]}]/best",
        "concurrent_fragment_downloads": 15,
        "outtmpl": f"{output_path}.%(ext)s",
        "verbose": logger.getEffectiveLevel() == logging.DEBUG,
        "cookiefile": cookie,
        "merge_output_format": "mkv",
        "writesubtitles": True,
    }
    logger.debug(f"Calling download with following options: {ydl_opts}")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download(url)


def is_normal_content(content: str) -> bool:
    """
    Check if the content is not a lab or feedback.

    :param content: The input content
    :return: True if the content is normal, False otherwise
    """
    is_lab = content.find("div", class_="start-lab-button")
    is_feedback = content.find_all("iframe")
    return not (is_lab or is_feedback)


def download_all_pdf(content, download_path: Path, cookie: str) -> None:
    """
    Download all PDF files from the given content.

    :param content: The content containing the PDF links
    :param download_path: The output directory for the downloaded PDFs
    :param cookie: The user's authentication cookie
    """
    for link in content.find_all("a"):
        href = link.get("href")
        if href.endswith("pdf"):
            file_name = download_path / Path(href).name
            logger.info(f"Downloading {file_name}...")
            response = requests.get(href, headers={"Cookie": cookie})
            file_name.write_bytes(response.content)


def file_hash(file_path: Path, hash_algorithm: str = "sha256") -> str:
    """
    Calculate the hash of a file using the specified algorithm.

    :param file_path: The path to the file
    :param hash_algorithm: The hashing algorithm to use (default: 'sha256')
    :return: The calculated hash as a hexadecimal string
    """
    hash_func = hashlib.new(hash_algorithm)
    with open(file_path, "rb") as file:
        while chunk := file.read(8192):
            hash_func.update(chunk)
    return hash_func.hexdigest()
