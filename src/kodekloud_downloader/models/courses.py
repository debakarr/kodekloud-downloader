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


class Course(BaseModel):
    id: str
    slug: str
    title: str
    thumbnail_url: HttpUrl
    tutors: List[Tutor]
    popularity: int
    difficulty_level: Optional[str]
    categories: List[Category]
    plan: str


class Metadata(BaseModel):
    limit: int
    page: int
    total_count: int
    next_page: Optional[int]


class ApiResponse(BaseModel):
    courses: List[Course]
    metadata: Metadata
