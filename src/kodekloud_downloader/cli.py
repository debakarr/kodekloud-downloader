import logging
from pathlib import Path
from typing import Optional, Union

import click
import validators

from kodekloud_downloader.enums import Quality
from kodekloud_downloader.helpers import select_courses
from kodekloud_downloader.main import (
    download_course,
    download_quiz,
    parse_course_from_url,
)
from kodekloud_downloader.models.helper import collect_all_courses


@click.group()
@click.option("-v", "--verbose", count=True, help="Increase log level verbosity")
def kodekloud(verbose):
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
    )
    if verbose == 1:
        logging.getLogger().setLevel(logging.INFO)
    elif verbose >= 2:
        logging.getLogger().setLevel(logging.DEBUG)


@kodekloud.command()
@click.argument("course_url", required=False)
@click.option(
    "--quality",
    "-q",
    default="1080p",
    type=click.Choice([quality.value for quality in Quality]),
    help="Quality of the video to be downloaded.",
)
@click.option(
    "--output-dir",
    "-o",
    default=Path.home() / "Downloads",
    help="Output directory where downloaded files will be store.",
)
@click.option(
    "--cookie",
    "-c",
    default=None,
    help="Cookie file exported from browser. Not needed with --browser.",
)
@click.option(
    "--browser",
    is_flag=True,
    default=False,
    help="Extract session token from running Chrome (requires playwright).",
)
@click.option(
    "--max-duplicate-count",
    "-mdc",
    default=3,
    type=int,
    help="If same video is downloaded this many times, then download stops",
)
def dl(
    course_url,
    quality: str,
    output_dir: Union[Path, str],
    cookie: Optional[str],
    browser: bool,
    max_duplicate_count: int,
):
    session_token: Optional[str] = None

    if browser:
        from kodekloud_downloader.browser import get_session_token_from_browser

        session_token = get_session_token_from_browser(auto_launch=True)
        if not session_token:
            logging.error(
                "Could not obtain session token from browser. "
                "Make sure Chrome is running with --remote-debugging-port=9222 "
                "and you are signed in to https://learn.kodekloud.com"
            )
            raise SystemExit(1)
        logging.info("Session token extracted from browser successfully")
    elif cookie:
        from kodekloud_downloader.helpers import parse_token

        session_token = parse_token(cookie)
        if not session_token:
            logging.error(
                "No session token found in cookie file. "
                "Try using --browser instead, or re-export your cookies. "
                "See README for instructions on adding session-cookie."
            )
            raise SystemExit(1)
    else:
        logging.error("Either --cookie or --browser must be provided")
        raise SystemExit(1)

    if course_url is None:
        courses = collect_all_courses()
        selected_courses = select_courses(courses)
        for selected_course in selected_courses:
            download_course(
                course=selected_course,
                quality=quality,
                output_dir=output_dir,
                max_duplicate_count=max_duplicate_count,
                session_token=session_token,
            )
    elif validators.url(course_url):
        course_detail = parse_course_from_url(course_url)
        download_course(
            course=course_detail,
            quality=quality,
            output_dir=output_dir,
            max_duplicate_count=max_duplicate_count,
            session_token=session_token,
        )
    else:
        logging.error("Please enter a valid URL")
        raise SystemExit(1)


@kodekloud.command()
@click.option(
    "--output-dir",
    "-o",
    default=Path.home() / "Downloads",
    help="Output directory where quiz markdown file will be saved.",
)
@click.option(
    "--sep",
    is_flag=True,
    show_default=True,
    default=False,
    help="Write in seperate markdown files.",
)
def dl_quiz(output_dir: Union[Path, str], sep: bool):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    download_quiz(output_dir, sep)


if __name__ == "__main__":
    kodekloud()
