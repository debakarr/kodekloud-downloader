import logging
from pathlib import Path
from typing import Union

import click
import validators

from kodekloud_downloader.enums import Quality
from kodekloud_downloader.helpers import select_courses
from kodekloud_downloader.main import download_course
from kodekloud_downloader.models import get_all_course


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
    required=True,
    help="Cookie file. Course should be accessible via this.",
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
    cookie,
    max_duplicate_count: int,
):
    if course_url is None:
        courses = get_all_course()
        selected_courses = select_courses(courses)
        for selected_course in selected_courses:
            download_course(
                url=selected_course.link,
                cookie=cookie,
                quality=quality,
                output_dir=output_dir,
                max_duplicate_count=max_duplicate_count,
            )
    elif validators.url(course_url):
        download_course(
            url=course_url,
            cookie=cookie,
            quality=quality,
            output_dir=output_dir,
            max_duplicate_count=max_duplicate_count,
        )
    else:
        logging.error("Please enter a valid URL")
        SystemExit(1)


if __name__ == "__main__":
    kodekloud()
