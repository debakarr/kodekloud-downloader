from dataclasses import dataclass
from typing import List

import requests
from bs4 import BeautifulSoup


@dataclass
class Lesson:
    name: str
    url: str
    is_video: bool


@dataclass
class Topic:
    name: str
    lessons: List[Lesson]

    @classmethod
    def make(cls, topic) -> "Topic":
        title = topic.find("h3", class_="lesson_title")
        name = title.text.strip()

        lessons_urls = topic.find_all("a", class_="ld-topic-row")
        lessons_names = topic.find_all("span", class_="ld-topic-title")

        lessons = []

        for lesson_url, lesson_name in zip(lessons_urls, lessons_names):
            is_video = "video_topic_enabled" in lesson_name["class"]
            lessons.append(
                Lesson(
                    name=lesson_name.text.strip(),
                    url=lesson_url["href"],
                    is_video=is_video,
                )
            )
        return cls(name=name, lessons=lessons)


@dataclass
class Course:
    name: str
    link: str
    course_type: str
    categories: List[str]

    @classmethod
    def make(cls, course_card) -> "Course":
        name = course_card.find("div", class_="text-size-20").text.strip()
        course_type = course_card.find_all("div", class_="course_type")[-1].text.strip()
        categories = [category.text.strip() for category in course_card.find_all("div", class_="course_category")]
        link = f"https://kodekloud.com/{course_card.find_all('a', class_='course_link')[-1].get('href')}"

        return cls(name=name, course_type=course_type, categories=categories, link=link)


def get_all_course() -> List[Course]:
    url = "https://kodekloud.com/courses/"
    response = requests.get(url)
    html_content = response.content
    soup = BeautifulSoup(html_content, "html.parser")

    course_cards = soup.find_all("div", class_="course_card")
    courses = []

    for card in course_cards:
        courses.append(Course.make(card))

    return courses
