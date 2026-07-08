"""
app/models/project.py

Project Showcase — students publish completed work (often, but not always,
their capstone) for others to browse, like, and comment on. Employers can
browse this without needing an account (read-only public access).
"""

from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class Project(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "projects"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    capstone_submission_id = Column(UUID(as_uuid=True), ForeignKey("capstone_submissions.id"), nullable=True)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    cover_image_url = Column(String, nullable=True)
    repo_url = Column(String, nullable=True)
    live_url = Column(String, nullable=True)

    is_published = Column(Boolean, default=True, nullable=False)
    like_count = Column(Integer, default=0, nullable=False)

    user = relationship("User", back_populates="projects")
    comments = relationship("ProjectComment", back_populates="project")

    def __repr__(self) -> str:
        return f"<Project {self.title}>"


class ProjectComment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "project_comments"

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)

    project = relationship("Project", back_populates="comments")

    def __repr__(self) -> str:
        return f"<ProjectComment project={self.project_id}>"
