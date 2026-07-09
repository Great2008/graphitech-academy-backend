"""
app/models/enrollment.py

Enrollment ties a User to a specific Course version. Progress tracks
per-lesson completion within that enrollment.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Boolean, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, UUIDMixin, TimestampMixin, EnrollmentStatus, pg_enum


class Enrollment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_user_course_enrollment"),)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)

    status = Column(pg_enum(EnrollmentStatus, "enrollmentstatus"), default=EnrollmentStatus.ACTIVE, nullable=False)
    enrolled_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # True once capstone approved AND (if required) all lesson/quiz pass marks met.
    # This is the field that unlocks the certificate purchase flow.
    is_eligible_for_certificate = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")
    progress_entries = relationship("Progress", back_populates="enrollment")

    def __repr__(self) -> str:
        return f"<Enrollment user={self.user_id} course={self.course_id} status={self.status}>"


class Progress(Base, UUIDMixin, TimestampMixin):
    """Per-lesson completion tracking within an enrollment."""
    __tablename__ = "progress"
    __table_args__ = (UniqueConstraint("enrollment_id", "lesson_id", name="uq_enrollment_lesson_progress"),)

    enrollment_id = Column(UUID(as_uuid=True), ForeignKey("enrollments.id"), nullable=False)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id"), nullable=False)

    is_completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    time_spent_seconds = Column(Integer, nullable=True)

    enrollment = relationship("Enrollment", back_populates="progress_entries")

    def __repr__(self) -> str:
        return f"<Progress lesson={self.lesson_id} completed={self.is_completed}>"
