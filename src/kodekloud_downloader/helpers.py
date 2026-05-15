import logging
import re
import string
from pathlib import Path
from typing import List, Optional

import prettytable
import requests
import yt_dlp

from kodekloud_downloader.models.courses import Course

logger = logging.getLogger(__name__)


def parse_input(input_str: str) -> List[int]:
    """
    Parse the input string and return a list of integers based on the given logic.

    :param input_str: A string representing the input ranges.
    :rtype: A list of integers.
    :raises ValueError: If an invalid range is encountered.

    Examples:
        >>> parse_input('1')
        [1]
        >>> parse_input('1-5')
        [1, 2, 3, 4, 5]
        >>> parse_input('1-3,6-8,10-11')
        [1, 2, 3, 6, 7, 8, 10, 11]
    """
    ranges = input_str.split(",")
    result: List[int] = []

    for r in ranges:
        if "-" in r:
            start, end = map(int, r.split("-"))
            if start > end:
                raise ValueError(f"Invalid range: {r}")
            result.extend(range(start, end + 1))
        else:
            result.append(int(r))

    return result


def select_courses(courses: List[Course]) -> List[Course]:
    """
    Display a table of courses and ask the user to select one or
    multiple courses by entering its number.

    :param courses: A list of Course objects to choose from
    :return: The selected list of Course object
    """
    table = prettytable.PrettyTable()
    table.field_names = ["No.", "Name", "Type", "Categories"]

    for i, course in enumerate(courses):
        table.add_row(
            [
                i + 1,
                course.title,
                course.plan,
                ", ".join([category.name for category in course.categories]),
            ]
        )

    table.align["No."] = "l"
    table.align["Name"] = "l"
    table.align["Type"] = "l"
    table.align["Categories"] = "l"

    print(table)

    user_selected_courses = []
    selected_courses = parse_input(
        input(
            "Enter the courses you want to select "
            "(Multiple courses can be passes using this format 1,6-9,10-11): "
        )
    )
    for selected_course in selected_courses:
        user_selected_courses.append(courses[int(selected_course) - 1])

    return user_selected_courses


# Characters not allowed in Windows filenames
_WINDOWS_RESERVED_CHARS = set('\\/:*?"<>|')
# Reserved names on Windows (case-insensitive, with/without extension)
_WINDOWS_RESERVED_NAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    "com1",
    "com2",
    "com3",
    "com4",
    "com5",
    "com6",
    "com7",
    "com8",
    "com9",
    "lpt1",
    "lpt2",
    "lpt3",
    "lpt4",
    "lpt5",
    "lpt6",
    "lpt7",
    "lpt8",
    "lpt9",
}


def sanitize_filename(name: str, max_length: int = 100) -> str:
    """Sanitize a string for use as a filename component.

    Removes or replaces characters that are invalid across platforms,
    trims whitespace, and truncates to ``max_length``.

    :param name: The raw string to sanitize.
    :param max_length: Maximum allowed length (default 100).
    :return: A safe filename string.
    """
    # Replace invalid characters with a safe alternative
    safe = "".join("_" if c in _WINDOWS_RESERVED_CHARS else c for c in name)
    # Collapse multiple underscores
    while "__" in safe:
        safe = safe.replace("__", "_")
    # Trim leading/trailing whitespace and dots
    safe = safe.strip(". ")
    # Truncate
    safe = safe[:max_length].rstrip(". ")
    # Handle empty result or reserved names
    if not safe or safe.lower().rstrip(".") in _WINDOWS_RESERVED_NAMES:
        safe = "_"
    return safe


def normalize_name(name: str) -> str:
    """
    Remove punctuation from a string.

    :param name: The input string
    :return: The string without punctuation
    """
    return name.translate(str.maketrans("", "", string.punctuation))


def download_video(
    url: str,
    output_path: Path,
    cookie: Optional[str],
    quality: str,
) -> None:
    """
    Download a video using yt_dlp with the given options.

    :param url: The video URL
    :param output_path: The output directory for the downloaded video
    :param cookie: The user's authentication cookie file path (None for
        browser-based auth)
    :param quality: The video quality (e.g. "720p")
    """
    headers = {
        "Referer": "https://learn.kodekloud.com/",
    }
    ydl_opts: dict = {
        "format": (
            f"bestvideo[height<={quality[:-1]}]+bestaudio/"
            f"best[height<={quality[:-1]}]/best"
        ),
        "concurrent_fragment_downloads": 15,
        "outtmpl": f"{output_path}.%(ext)s",
        "verbose": logger.getEffectiveLevel() == logging.DEBUG,
        "merge_output_format": "mkv",
        "writesubtitles": True,
        "no_write_sub": True,
        "http_headers": headers,
    }
    if cookie is not None:
        ydl_opts["cookiefile"] = cookie
    logger.debug(f"Calling download with following options: {ydl_opts}")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download(url)


def is_normal_content(content) -> bool:
    """
    Check if the content is not a lab or feedback.

    :param content: The input content (BeautifulSoup Tag)
    :return: True if the content is normal, False otherwise
    """
    is_lab = content.find("div", class_="start-lab-button")
    is_feedback = content.find_all("iframe")
    return not (is_lab or is_feedback)


def download_all_pdf(content, download_path: Path, cookie: Optional[str]) -> None:
    """
    Download all PDF files from the given content.

    :param content: The content containing the PDF links
    :param download_path: The output directory for the downloaded PDFs
    :param cookie: The user's authentication cookie (None for browser auth)
    """
    for link in content.find_all("a"):
        href = link.get("href")
        if href.endswith("pdf"):
            file_name = download_path / Path(href).name
            logger.info(f"Downloading {file_name}...")
            headers = {}
            if cookie is not None:
                headers["Cookie"] = cookie
            response = requests.get(href, headers=headers, timeout=30)
            file_name.write_bytes(response.content)


def parse_token(cookiefile: str) -> Optional[str]:
    """
    Parse the session cookie from a file containing cookies.

    :param cookiefile: The path to the file containing cookies.
    :return: The value of the session cookie if found, otherwise None.
    :raises FileNotFoundError: If the cookie file does not exist.
    :raises IOError: If there is an error reading the file.
    """
    cookies = {}
    try:
        with open(cookiefile) as fp:
            for line in fp:
                if line.strip() and not re.match(r"^\#", line):
                    line_fields = line.strip().split("\t")
                    if len(line_fields) > 6:
                        cookies[line_fields[5]] = line_fields[6]
    except FileNotFoundError:
        raise FileNotFoundError(f"The file {cookiefile} does not exist.") from None
    except OSError as e:
        raise OSError(f"Error reading the file {cookiefile}: {e}") from e

    return cookies.get("session-cookie") or cookies.get("_secure-user-session")
