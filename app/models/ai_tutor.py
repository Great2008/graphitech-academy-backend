"""
app/models/ai_tutor.py

Tracks every AI tutor interaction for:
  - Rate limiting free-tier users
  - Identifying premium-conversion candidates (users hitting limits often)
  - AI safety logging (privacy-respecting — no full prompt/response stored
    by default, just metadata; see PROMPT_LOG_MODE)

low_confidence_flag lets the tutor UI show a disclaimer when the model's
own response indicated uncertainty.
"""

from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class TutorUsage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tutor_usage"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=True)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id"), nullable=True)

    # Metadata only by default — respects privacy while still useful for
    # rate limiting and product analytics.
    prompt_char_count = Column(Integer, nullable=True)
    response_char_count = Column(Integer, nullable=True)
    prompt_excerpt = Column(Text, nullable=True)  # optional short excerpt, only if user opts in to full logging

    model_used = Column(String, nullable=True)  # e.g. "groq/llama-3.1", "claude-sonnet"
    low_confidence_flag = Column(Boolean, default=False, nullable=False)
    flagged_for_plagiarism_risk = Column(Boolean, default=False, nullable=False)  # e.g. "write my quiz answer" style asks

    is_premium_request = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="tutor_usage")

    def __repr__(self) -> str:
        return f"<TutorUsage user={self.user_id} premium={self.is_premium_request}>"
