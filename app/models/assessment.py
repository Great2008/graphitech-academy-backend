"""
app/models/assessment.py

Quizzes (per-lesson) and Capstone submissions (per-course, gates the
certificate). Capstones can be auto-graded (e.g. test suite passes) or
manually reviewed by an Instructor/Reviewer.
"""

from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, UUIDMixin, TimestampMixin, QuizAttemptStatus, CapstoneStatus


class Quiz(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "quizzes"

    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id"), nullable=False)

    title = Column(String, nullable=False)
    pass_mark_percent = Column(Integer, default=70, nullable=False)

    # Questions stored as structured JSON:
    # [{ "question": "...", "options": [...], "correct_index": 0 }, ...]
    questions = Column(JSON, nullable=False)

    lesson = relationship("Lesson", back_populates="quizzes")
    attempts = relationship("QuizAttempt", back_populates="quiz")

    def __repr__(self) -> str:
        return f"<Quiz {self.title}>"


class QuizAttempt(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "quiz_attempts"

    quiz_id = Column(UUID(as_uuid=True), ForeignKey("quizzes.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    score_percent = Column(Integer, nullable=False)
    status = Column(Enum(QuizAttemptStatus), default=QuizAttemptStatus.IN_PROGRESS, nullable=False)
    answers = Column(JSON, nullable=True)  # submitted answers, for review/analytics
    submitted_at = Column(DateTime(timezone=True), nullable=True)

    quiz = relationship("Quiz", back_populates="attempts")
    user = relationship("User", back_populates="quiz_attempts")

    def __repr__(self) -> str:
        return f"<QuizAttempt user={self.user_id} score={self.score_percent} status={self.status}>"


class CapstoneSubmission(Base, UUIDMixin, TimestampMixin):
    """
    Gates certificate eligibility. A course with requires_capstone=True
    will not mark an Enrollment as certificate-eligible until a submission
    here reaches CapstoneStatus.APPROVED.
    """
    __tablename__ = "capstone_submissions"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    repo_url = Column(String, nullable=True)
    live_url = Column(String, nullable=True)

    status = Column(Enum(CapstoneStatus), default=CapstoneStatus.SUBMITTED, nullable=False)

    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewer_feedback = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # If auto-graded (e.g. via test runner), store raw results here.
    auto_grade_result = Column(JSON, nullable=True)

    user = relationship("User", back_populates="capstone_submissions", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<CapstoneSubmission {self.title} status={self.status}>"
