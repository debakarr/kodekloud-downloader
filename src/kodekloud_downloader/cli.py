import base64
import json
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
    "--token",
    "-t",
    default=None,
    help="Direct Firebase JWT authentication token.",
)
@click.option(
    "--max-duplicate-count",
    "-mdc",
    default=3,
    type=int,
    help="If same video is downloaded this many times, then download stops",
)
@click.option(
    "--search",
    "-s",
    default=None,
    help="Filter course list by keyword (title, instructor, or category).",
)
@click.option(
    "--filter",
    "-f",
    "--category",
    "category_filter",
    default=None,
    help=(
        "Filter course list by category "
        "(e.g. 'Kubernetes', 'Security', 'Golden Kubestronaut')."
    ),
)
def dl(
    course_url,
    quality: str,
    output_dir: Union[Path, str],
    cookie: Optional[str],
    browser: bool,
    token: Optional[str],
    max_duplicate_count: int,
    search: Optional[str],
    category_filter: Optional[str],
):
    session_token: Optional[str] = None

    if token:
        session_token = token
        logging.info("Using session token provided via CLI")
    elif browser:
        from kodekloud_downloader.browser import get_session_token_from_browser

        session_token = get_session_token_from_browser(auto_launch=True)
        if not session_token:
            msg = (
                "Could not obtain session token from browser. "
                "Make sure Chrome is running with --remote-debugging-port=9222 "
                "and you are signed in to https://learn.kodekloud.com"
            )
            logging.error(msg)
            click.echo(msg, err=True)
            raise SystemExit(1)
        logging.info("Session token extracted from browser successfully")
    elif cookie:
        from kodekloud_downloader.helpers import parse_token

        raw_token = parse_token(cookie)
        is_valid_id_token = False
        if raw_token and raw_token.startswith("ey") and len(raw_token.split(".")) == 3:
            try:
                _, payload, _ = raw_token.split(".")
                payload += "=" * (-len(payload) % 4)
                jwt_data = json.loads(base64.b64decode(payload))
                if "session.firebase" not in jwt_data.get("iss", ""):
                    is_valid_id_token = True
            except Exception as err:
                logging.debug("Could not decode JWT payload: %s", err)

        if is_valid_id_token:
            session_token = raw_token
        else:
            logging.info("Resolving Firebase ID token from cookie file via browser...")
            click.echo("Authenticating session from cookies...", err=True)
            from kodekloud_downloader.browser import get_token_from_cookie_file

            session_token = get_token_from_cookie_file(cookie)
            if not session_token:
                msg = (
                    "Could not extract session token from cookie file. "
                    "Make sure your cookie file contains valid session cookies, "
                    "or try using --browser / --token."
                )
                logging.error(msg)
                click.echo(msg, err=True)
                raise SystemExit(1)
            logging.info("Session token resolved successfully from cookies")

    else:
        msg = "Either --cookie, --browser, or --token must be provided"
        logging.error(msg)
        click.echo(msg, err=True)
        raise SystemExit(1)

    assert session_token is not None

    if course_url is None:
        courses = collect_all_courses()
        selected_courses = select_courses(
            courses, query=search, category=category_filter
        )
        for selected_course in selected_courses:
            download_course(
                course=selected_course,
                quality=quality,
                output_dir=output_dir,
                max_duplicate_count=max_duplicate_count,
                session_token=session_token,
                cookie=cookie,
            )
    elif validators.url(course_url):
        course_detail = parse_course_from_url(course_url)
        download_course(
            course=course_detail,
            quality=quality,
            output_dir=output_dir,
            max_duplicate_count=max_duplicate_count,
            session_token=session_token,
            cookie=cookie,
        )
    else:
        msg = "Please enter a valid URL"
        logging.error(msg)
        click.echo(msg, err=True)
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
