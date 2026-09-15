import logging
import re
import string
import urllib.parse
from collections import defaultdict
from pathlib import Path
from typing import Any, List, Optional, Set, Tuple, Union, cast

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


def render_course_table(
    indexed_courses: List[Tuple[int, Course]],
) -> prettytable.PrettyTable:
    """
    Build a PrettyTable displaying course numbers, titles, instructors, types,
    and categories.

    :param indexed_courses: List of (1-based index, Course) tuples
    :return: Formatted PrettyTable instance
    """
    table = prettytable.PrettyTable()
    table.field_names = ["No.", "Name", "Instructor", "Type", "Categories"]

    for original_idx, course in indexed_courses:
        instructor_str = ", ".join([tutor.name for tutor in course.tutors]) or "N/A"
        category_str = ", ".join([cat.name for cat in course.categories])
        table.add_row(
            [
                original_idx,
                course.title,
                instructor_str,
                course.plan,
                category_str,
            ]
        )

    table.align["No."] = "l"
    table.align["Name"] = "l"
    table.align["Instructor"] = "l"
    table.align["Type"] = "l"
    table.align["Categories"] = "l"
    return table


def _to_indexed(
    courses: Union[List[Course], List[Tuple[int, Course]]],
) -> List[Tuple[int, Course]]:
    """Ensure list is in (1-based index, Course) format."""
    if not courses:
        return []
    first = courses[0]
    if isinstance(first, tuple) and len(first) == 2 and isinstance(first[0], int):
        return cast(List[Tuple[int, Course]], courses)
    return list(enumerate(cast(List[Course], courses), start=1))


def filter_by_category(
    courses: Union[List[Course], List[Tuple[int, Course]]],
    category_query: str,
) -> List[Tuple[int, Course]]:
    """Filter courses by category matching any comma-separated token.

    :param courses: List of Course objects or (index, Course) tuples.
    :param category_query: Comma-separated category keywords.
    :return: Filtered list of (1-based index, Course) tuples.
    """
    indexed = _to_indexed(courses)
    tokens = [t.strip().lower() for t in category_query.split(",") if t.strip()]
    if not tokens:
        return indexed

    matches: List[Tuple[int, Course]] = []
    for idx, course in indexed:
        cat_names = [cat.name.lower() for cat in course.categories]
        if any(any(tok in cat for cat in cat_names) for tok in tokens):
            matches.append((idx, course))
    return matches


def render_categories_summary(courses: List[Course]) -> prettytable.PrettyTable:
    """Build a summary table of all unique categories and their course counts."""
    counts: dict = defaultdict(int)
    for course in courses:
        for cat in course.categories:
            counts[cat.name] += 1

    table = prettytable.PrettyTable()
    table.field_names = ["Category", "Courses"]
    for cat_name, count in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
        table.add_row([cat_name, count])
    table.align["Category"] = "l"
    table.align["Courses"] = "r"
    return table


def _filter_courses(
    courses: Union[List[Course], List[Tuple[int, Course]]],
    query: str,
) -> List[Tuple[int, Course]]:
    """Filter courses by keyword across title, instructor, category, and slug."""
    indexed = _to_indexed(courses)
    q = query.strip().lower()
    matches: List[Tuple[int, Course]] = []
    for idx, course in indexed:
        title = course.title.lower()
        slug = course.slug.lower()
        instructors = " ".join([t.name.lower() for t in course.tutors])
        categories = " ".join([c.name.lower() for c in course.categories])
        if q in title or q in slug or q in instructors or q in categories:
            matches.append((idx, course))
    return matches


def select_courses(
    courses: List[Course],
    query: Optional[str] = None,
    category: Optional[str] = None,
) -> List[Course]:
    """
    Display a table of courses and ask the user to select one or
    multiple courses by entering its number, or filter interactively
    by keyword/category.

    :param courses: A list of Course objects to choose from
    :param query: Optional initial search term to pre-filter courses
    :param category: Optional initial category filter (comma-separated supported)
    :return: The selected list of Course objects
    """
    indexed_all: List[Tuple[int, Course]] = list(enumerate(courses, start=1))

    current_items = indexed_all
    if category:
        filtered_cat = filter_by_category(current_items, category)
        if not filtered_cat:
            print(
                f"No courses found matching category filter '{category}'. "
                "Showing all courses."
            )
        else:
            current_items = filtered_cat

    if query:
        filtered_query = _filter_courses(current_items, query)
        if not filtered_query:
            print(
                f"No courses found matching search filter '{query}'. "
                "Showing previous view."
            )
        else:
            current_items = filtered_query

    print(render_course_table(current_items))

    while True:
        prompt = (
            "Enter course number(s) to select (e.g. 1,6-9), "
            "search keyword, 'c:<cat>', or 'all'/'cats'/'q': "
        )
        try:
            user_input = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return []

        if not user_input:
            continue

        if user_input.lower() in ("q", "quit", "exit"):
            return []

        if user_input.lower() == "all":
            current_items = indexed_all
            print(render_course_table(current_items))
            continue

        if user_input.lower() in ("cats", "categories"):
            print(render_categories_summary(courses))
            continue

        if user_input.lower().startswith(("c:", "cat:", "category:")):
            cat_query = user_input.split(":", 1)[1].strip()
            filtered = filter_by_category(indexed_all, cat_query)
            if filtered:
                current_items = filtered
                print(render_course_table(current_items))
                print(
                    f"Found {len(filtered)} course(s) in category matching "
                    f"'{cat_query}'."
                )
            else:
                print(
                    f"No courses found in category matching '{cat_query}'. "
                    "Type 'cats' to see all categories."
                )
            continue

        try:
            selected_indices = parse_input(user_input)
            invalid = [i for i in selected_indices if i < 1 or i > len(courses)]
            if invalid:
                print(
                    f"Error: Course number(s) {invalid} out of range "
                    f"(1 - {len(courses)})."
                )
                continue
            return [courses[i - 1] for i in selected_indices]
        except ValueError:
            # User entered a search term instead of numeric range
            filtered = _filter_courses(indexed_all, user_input)
            if filtered:
                current_items = filtered
                print(render_course_table(current_items))
                print(f"Found {len(filtered)} course(s) matching '{user_input}'.")
            else:
                print(f"No courses found matching '{user_input}'. Try another search.")


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


RESOURCE_EXTENSIONS: Tuple[str, ...] = (
    ".pdf",
    ".zip",
    ".tar.gz",
    ".tgz",
    ".tar",
    ".gz",
    ".7z",
    ".rar",
    ".pptx",
    ".ppt",
    ".docx",
    ".doc",
    ".xlsx",
    ".xls",
    ".csv",
    ".epub",
    ".ipynb",
    ".yaml",
    ".yml",
    ".json",
    ".sh",
    ".py",
    ".txt",
)


def _is_resource_target(url_or_name: str) -> bool:
    """Check if a URL or name ends with a known resource extension."""
    clean = url_or_name.lower().split("?")[0].split("#")[0].strip()
    return any(clean.endswith(ext) for ext in RESOURCE_EXTENSIONS)


def normalize_resource_url(url: str) -> str:
    """
    Normalize URLs for direct downloading.
    Converts GitHub blob URLs (e.g. github.com/owner/repo/blob/ref/path)
    to raw URLs (raw.githubusercontent.com/owner/repo/ref/path).

    :param url: The resource URL.
    :return: Normalized direct download URL.
    """
    github_blob_match = re.match(
        r"^https?://github\.com/([^/]+)/([^/]+)/blob/(.+)$", url
    )
    if github_blob_match:
        owner, repo, rest = github_blob_match.groups()
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{rest}"
    return url


def extract_resource_urls(content: Any) -> List[Tuple[str, str]]:
    """
    Extract (url, title_or_text) pairs for downloadable resources from Markdown or HTML.

    :param content: Markdown string or BeautifulSoup element
    :return: List of tuples (url, link_text)
    """
    results: List[Tuple[str, str]] = []
    seen_urls: Set[str] = set()

    if hasattr(content, "find_all"):
        # BeautifulSoup tag or document
        for link in content.find_all("a"):
            href = link.get("href")
            if href and isinstance(href, str) and href.startswith("http"):
                text = link.get_text(strip=True)
                if _is_resource_target(href) or _is_resource_target(text):
                    norm_url = normalize_resource_url(href)
                    if norm_url not in seen_urls:
                        seen_urls.add(norm_url)
                        results.append((norm_url, text))
    elif isinstance(content, str):
        # Markdown links: [Link Text](https://url)
        md_links = re.findall(r"(?<!!)\[([^\]]*)\]\((https?://[^\s\)\"\']+)\)", content)
        for text, url in md_links:
            if _is_resource_target(url) or _is_resource_target(text):
                norm_url = normalize_resource_url(url)
                if norm_url not in seen_urls:
                    seen_urls.add(norm_url)
                    results.append((norm_url, text))

        # Bare URLs: https://...
        bare_urls = re.findall(r"(https?://[^\s\"\'<>\[\]\)]+)", content)
        for url in bare_urls:
            if _is_resource_target(url):
                norm_url = normalize_resource_url(url)
                if norm_url not in seen_urls:
                    seen_urls.add(norm_url)
                    results.append((norm_url, ""))

    return results


def _resolve_resource_filename(url: str, title: str = "") -> str:
    """Resolve a sanitized filename from a URL and an optional link title."""
    parsed = urllib.parse.urlparse(url)
    url_filename = Path(urllib.parse.unquote(parsed.path)).name

    if _is_resource_target(url_filename) and url_filename:
        target_name = url_filename
    elif title and _is_resource_target(title):
        target_name = title
    elif url_filename:
        target_name = url_filename
    else:
        target_name = "resource.bin"

    return sanitize_filename(target_name)


def download_all_resources(
    content: Any,
    download_path: Path,
    cookie: Optional[str] = None,
    session_token: Optional[str] = None,
) -> List[Path]:
    """
    Download all resources (PDFs, archives, documents, etc.) from the given content.

    :param content: Markdown string or BeautifulSoup element containing resource links
    :param download_path: The directory where downloaded resources will be saved
    :param cookie: The user's authentication cookie
    :param session_token: Optional Bearer session token for authenticated downloads
    :return: List of Paths of downloaded files
    """
    downloaded_files: List[Path] = []
    items = extract_resource_urls(content)

    if not items:
        return downloaded_files

    logger.info(f"Found {len(items)} downloadable resource(s) attached.")
    download_path.mkdir(parents=True, exist_ok=True)
    headers: dict = {}
    if session_token:
        headers["Authorization"] = f"Bearer {session_token}"
    elif cookie is not None:
        headers["Cookie"] = cookie

    for url, title in items:
        url = normalize_resource_url(url)
        file_name = _resolve_resource_filename(url, title)
        target_path = download_path / file_name

        if target_path.exists() and target_path.stat().st_size > 0:
            logger.info(f"Resource {file_name} already exists, skipping...")
            downloaded_files.append(target_path)
            continue

        logger.info(f"Downloading resource: {file_name} from {url}...")
        try:
            resp = requests.get(url, headers=headers, stream=True, timeout=60)
            resp.raise_for_status()
            with open(target_path, "wb") as f:
                wrote_bytes = False
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        wrote_bytes = True
                if not wrote_bytes and hasattr(resp, "content") and resp.content:
                    f.write(resp.content)
            downloaded_files.append(target_path)
            logger.info(f"Saved resource: {target_path}")
        except Exception as ex:
            logger.warning(f"Failed to download resource from {url}: {ex}")

    return downloaded_files


def download_all_pdf(
    content: Any,
    download_path: Path,
    cookie: Optional[str] = None,
    session_token: Optional[str] = None,
) -> None:
    """
    Download all PDF files from the given content.
    Retained for backwards compatibility; delegates to download_all_resources.
    """
    download_all_resources(
        content=content,
        download_path=download_path,
        cookie=cookie,
        session_token=session_token,
    )


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
