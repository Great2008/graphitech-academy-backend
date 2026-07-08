"""
app/models/user.py

User model. Fields are split conceptually into public (safe to expose on
/u/{username} portfolio pages) and private (email, payment info, internal
flags) — enforced in the Pydantic schema layer, not here.
"""

from sqlalchemy import Column, String, Boolean, Enum, Text
from sqlalchemy.orm import relationship

from app.models.base import Base, UUIDMixin, TimestampMixin, UserRole


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    # --- Private fields (never exposed on public portfolio) ---
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=True)  # nullable if using OAuth/Supabase auth
    phone_number = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # --- Role / access control ---
    role = Column(Enum(UserRole), default=UserRole.STUDENT, nullable=False)

    # --- Public fields (safe for /u/{username}) ---
    username = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    github_url = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    state = Column(String, nullable=True)  # for grant-readiness "states reached" metric
    gender = Column(String, nullable=True)  # optional, for women-in-tech impact metrics

    # --- Relationships ---
    enrollments = relationship("Enrollment", back_populates="user")
    quiz_attempts = relationship("QuizAttempt", back_populates="user")
    capstone_submissions = relationship("CapstoneSubmission", back_populates="user")
    certificates = relationship("Certificate", back_populates="user")
    badges = relationship("UserBadge", back_populates="user")
    projects = relationship("Project", back_populates="user")
    tutor_usage = relationship("TutorUsage", back_populates="user")

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role})>"
