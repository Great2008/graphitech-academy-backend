"""
app/schemas/project.py
"""

from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import ORMBase, TimestampedRead
from app.schemas.user import UserPublic


class ProjectCreate(BaseModel):
    capstone_submission_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    repo_url: Optional[str] = None
    live_url: Optional[str] = None


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    repo_url: Optional[str] = None
    live_url: Optional[str] = None
    is_published: Optional[bool] = None


class ProjectCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=1000)


class ProjectCommentRead(TimestampedRead):
    project_id: UUID
    user: UserPublic
    body: str


class ProjectRead(TimestampedRead):
    user: UserPublic
    title: str
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    repo_url: Optional[str] = None
    live_url: Optional[str] = None
    is_published: bool
    like_count: int


class ProjectWithComments(ProjectRead):
    comments: List[ProjectCommentRead] = []
