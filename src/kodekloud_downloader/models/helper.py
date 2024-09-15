from typing import List

import requests

from kodekloud_downloader.models.course import CourseDetail
from kodekloud_downloader.models.courses import ApiResponse, Course


def fetch_courses(page: int, limit: int) -> ApiResponse:
    url = f"https://learn-api.kodekloud.com/api/courses?page={page}&limit={limit}"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    return ApiResponse(**data)


def collect_all_courses() -> List[Course]:
    all_courses = []
    page = 1
    limit = 30
    while True:
        api_response = fetch_courses(page, limit)
        all_courses.extend(api_response.courses)
        if api_response.metadata.next_page is None:
            break
        page = api_response.metadata.next_page
    return all_courses


def fetch_course_detail(slug: str) -> CourseDetail:
    url = f"https://learn-api.kodekloud.com/api/courses/{slug}"
    response = requests.get(url)
    response.raise_for_status()  # Raise an exception for HTTP errors
    data = response.json()

    return CourseDetail(**data)


# Example usage
if __name__ == "__main__":
    courses = collect_all_courses()
    for course in courses:
        course_detail = fetch_course_detail(course.slug)
        print(course_detail.title)
        print(course_detail.description)
        print(course_detail.modules)
        break
