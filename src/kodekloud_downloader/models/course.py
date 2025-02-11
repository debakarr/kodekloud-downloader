from typing import List, Optional

from pydantic import BaseModel, HttpUrl


class Category(BaseModel):
    id: str
    name: str


class Tutor(BaseModel):
    id: str
    name: str
    bio: str
    description: str
    avatar_url: HttpUrl


class Lesson(BaseModel):
    id: str
    title: str
    type: str  # e.g., "video", "lab", "quiz"
    position: int
    duration: Optional[int] = 0  # Duration is optional and may not be present


class Module(BaseModel):
    id: str
    title: str
    position: int
    lessons_count: int
    lessons: List[Lesson]


class IncludesSection(BaseModel):
    modules_count: int
    lessons_count: int
    lab_lessons: bool
    lab_lesson_count: int
    quiz_lessons: bool
    quiz_lesson_count: int
    mock_exams: bool
    community_support: Optional[bool] = None
    hours_of_video: int


class CourseDetail(BaseModel):
    id: str
    slug: str
    title: str
    thumbnail_url: HttpUrl
    tutors: List[Tutor]
    popularity: int
    difficulty_level: Optional[str]
    categories: List[Category]
    plan: str
    excerpt: Optional[str]
    description: str
    lessons_count: int
    userback_id: Optional[str]
    hidden: bool
    modules: List[Module]
    includes_section: IncludesSection
