"""
app/models/badge.py

Badges are lighter-weight than certificates — awarded automatically on
triggers (e.g. "complete HTML course" -> "HTML Beginner" badge) and shown
on the public portfolio / achievement timeline.
"""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class Badge(Base, UUIDMixin, TimestampMixin):
    """A badge definition, e.g. 'React Developer'."""
    __tablename__ = "badges"

    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    icon_url = Column(String, nullable=True)

    # Simple trigger reference, e.g. "course_completed:react-fundamentals"
    # or "manual" for things like "Community Mentor" awarded by an admin.
    trigger_key = Column(String, nullable=True)

    user_badges = relationship("UserBadge", back_populates="badge")

    def __repr__(self) -> str:
        return f"<Badge {self.name}>"


class UserBadge(Base, UUIDMixin, TimestampMixin):
    """A badge earned by a specific user."""
    __tablename__ = "user_badges"
    __table_args__ = (UniqueConstraint("user_id", "badge_id", name="uq_user_badge"),)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    badge_id = Column(UUID(as_uuid=True), ForeignKey("badges.id"), nullable=False)
    earned_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="badges")
    badge = relationship("Badge", back_populates="user_badges")

    def __repr__(self) -> str:
        return f"<UserBadge user={self.user_id} badge={self.badge_id}>"
