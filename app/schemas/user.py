"""
app/schemas/user.py

UserPublic is the ONLY schema that should ever be returned from the public
/u/{username} portfolio route — it deliberately excludes email, phone,
role, is_verified, and anything else private. Do not add private fields
to it without a deliberate reason.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.base import ORMBase, TimestampedRead, UserRole


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=8)
    display_name: Optional[str] = None


class UserUpdate(BaseModel):
    """Fields a user can edit on their own profile."""
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = Field(default=None, max_length=500)
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    state: Optional[str] = None
    gender: Optional[str] = None


class UserRoleUpdate(BaseModel):
    """Admin/Super Admin only — changes a user's role."""
    role: UserRole


class UserRead(TimestampedRead):
    """Full read schema — for the authenticated user viewing their own account, or Admins."""
    email: EmailStr
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    role: UserRole
    is_active: bool
    is_verified: bool
    state: Optional[str] = None
    gender: Optional[str] = None


class UserPublic(ORMBase):
    """
    Public portfolio schema for GET /u/{username}.
    No email, no phone, no role, no verification status, no id-adjacent
    internal fields beyond what's needed to link related public data.
    """
    id: UUID
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
