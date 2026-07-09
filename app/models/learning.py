"""
app/models/learning.py

Learning Paths, Courses, and Lessons.

Courses are versioned: editing a published course creates a new version
rather than mutating it in place, so students already enrolled in v1 can
finish v1 while new enrollments go to the latest version.
"""

from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, UUIDMixin, TimestampMixin, CourseStatus, pg_enum


class LearningPath(Base, UUIDMixin, TimestampMixin):
    """A larger goal made up of multiple courses, e.g. 'Frontend Development'."""
    __tablename__ = "learning_paths"

    title = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    icon_url = Column(String, nullable=True)
    order_index = Column(Integer, default=0)  # display order on the paths page
    is_published = Column(Boolean, default=False, nullable=False)

    courses = relationship("Course", back_populates="learning_path", order_by="Course.order_index")

    def __repr__(self) -> str:
        return f"<LearningPath {self.title}>"


class Course(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "courses"

    learning_path_id = Column(UUID(as_uuid=True), ForeignKey("learning_paths.id"), nullable=True)

    title = Column(String, nullable=False)
    slug = Column(String, nullable=False, index=True)  # not globally unique — versions share a slug
    description = Column(Text, nullable=True)
    thumbnail_url = Column(String, nullable=True)

    # --- Versioning ---
    version = Column(Integer, default=1, nullable=False)
    is_latest_version = Column(Boolean, default=True, nullable=False)
    previous_version_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=True)

    status = Column(pg_enum(CourseStatus, "coursestatus"), default=CourseStatus.DRAFT, nullable=False)
    order_index = Column(Integer, default=0)

    pass_mark_percent = Column(Integer, default=70, nullable=False)  # course-level pass mark
    certificate_fee_kobo = Column(Integer, nullable=True)  # flat fee in kobo (NGN minor unit); null = free

    requires_capstone = Column(Boolean, default=True, nullable=False)

    # --- AI generation provenance ---
    generated_by_ai = Column(Boolean, default=False, nullable=False)
    ai_source_prompt = Column(Text, nullable=True)  # what was fed to Groq to draft this

    # --- Relationships ---
    learning_path = relationship("LearningPath", back_populates="courses")
    lessons = relationship("Lesson", back_populates="course", order_by="Lesson.order_index")
    enrollments = relationship("Enrollment", back_populates="course")

    def __repr__(self) -> str:
        return f"<Course {self.title} v{self.version}>"


class Lesson(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "lessons"

    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)

    title = Column(String, nullable=False)
    order_index = Column(Integer, default=0, nullable=False)

    # Content stored as Markdown, rendered client-side/server-side to HTML.
    # Enables versioning, diffing, search indexing, and AI-assisted editing.
    content_markdown = Column(Text, nullable=False)

    video_url = Column(String, nullable=True)
    estimated_minutes = Column(Integer, nullable=True)

    has_quiz = Column(Boolean, default=False, nullable=False)
    has_playground = Column(Boolean, default=False, nullable=False)
    playground_starter_code = Column(Text, nullable=True)
    playground_language = Column(String, nullable=True)  # e.g. "python", "javascript"

    is_downloadable = Column(Boolean, default=True, nullable=False)  # offline reading, licensing permitting

    course = relationship("Course", back_populates="lessons")
    quizzes = relationship("Quiz", back_populates="lesson")

    def __repr__(self) -> str:
        return f"<Lesson {self.title}>"
