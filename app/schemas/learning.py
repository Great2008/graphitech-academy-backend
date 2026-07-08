"""
app/schemas/learning.py

Schemas for Learning Paths, Courses, and Lessons — including the input
schema for the Admin "Add Course" AI-draft flow.
"""

from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import ORMBase, TimestampedRead, CourseStatus


# --- Learning Path ---

class LearningPathCreate(BaseModel):
    title: str
    slug: str
    description: Optional[str] = None
    icon_url: Optional[str] = None
    order_index: int = 0


class LearningPathUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    icon_url: Optional[str] = None
    order_index: Optional[int] = None
    is_published: Optional[bool] = None


class LearningPathRead(TimestampedRead):
    title: str
    slug: str
    description: Optional[str] = None
    icon_url: Optional[str] = None
    order_index: int
    is_published: bool


# --- Lesson ---

class LessonCreate(BaseModel):
    title: str
    order_index: int = 0
    content_markdown: str
    video_url: Optional[str] = None
    estimated_minutes: Optional[int] = None
    has_quiz: bool = False
    has_playground: bool = False
    playground_starter_code: Optional[str] = None
    playground_language: Optional[str] = None
    is_downloadable: bool = True


class LessonUpdate(BaseModel):
    title: Optional[str] = None
    order_index: Optional[int] = None
    content_markdown: Optional[str] = None
    video_url: Optional[str] = None
    estimated_minutes: Optional[int] = None
    has_quiz: Optional[bool] = None
    has_playground: Optional[bool] = None
    playground_starter_code: Optional[str] = None
    playground_language: Optional[str] = None
    is_downloadable: Optional[bool] = None


class LessonRead(TimestampedRead):
    course_id: UUID
    title: str
    order_index: int
    content_markdown: str
    video_url: Optional[str] = None
    estimated_minutes: Optional[int] = None
    has_quiz: bool
    has_playground: bool
    playground_starter_code: Optional[str] = None
    playground_language: Optional[str] = None
    is_downloadable: bool


# --- Course ---

class CourseCreate(BaseModel):
    """Manual course creation (no AI draft)."""
    learning_path_id: Optional[UUID] = None
    title: str
    slug: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    pass_mark_percent: int = Field(default=70, ge=0, le=100)
    certificate_fee_kobo: Optional[int] = Field(default=None, ge=0)
    requires_capstone: bool = True


class CourseAIDraftRequest(BaseModel):
    """
    Input for the Admin 'Add Course' AI-draft flow. Groq drafts an outline
    + lessons from this; an Instructor/Admin then reviews and edits before
    publishing. Nothing here is saved until the reviewer approves it.
    """
    topic: str = Field(..., description="e.g. 'React fundamentals for beginners'")
    learning_path_id: Optional[UUID] = None
    target_lesson_count: int = Field(default=8, ge=1, le=40)
    audience_level: str = Field(default="beginner", description="beginner | intermediate | advanced")
    include_quizzes: bool = True
    include_capstone: bool = True
    additional_instructions: Optional[str] = None


class CourseUpdate(BaseModel):
    """Editing a published course creates a new version — see CourseService.create_new_version."""
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    status: Optional[CourseStatus] = None
    pass_mark_percent: Optional[int] = Field(default=None, ge=0, le=100)
    certificate_fee_kobo: Optional[int] = Field(default=None, ge=0)
    requires_capstone: Optional[bool] = None
    order_index: Optional[int] = None


class CourseRead(TimestampedRead):
    learning_path_id: Optional[UUID] = None
    title: str
    slug: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    version: int
    is_latest_version: bool
    status: CourseStatus
    order_index: int
    pass_mark_percent: int
    certificate_fee_kobo: Optional[int] = None
    requires_capstone: bool
    generated_by_ai: bool


class CourseWithLessons(CourseRead):
    lessons: List[LessonRead] = []


class LearningPathWithCourses(LearningPathRead):
    courses: List[CourseRead] = []
