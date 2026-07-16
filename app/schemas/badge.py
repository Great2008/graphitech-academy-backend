"""
app/schemas/badge.py
"""

from typing import Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel

from app.schemas.base import ORMBase, TimestampedRead


class BadgeCreate(BaseModel):
    """Admin only — defines a new badge type."""
    name: str
    description: Optional[str] = None
    icon_url: Optional[str] = None
    trigger_key: Optional[str] = None


class BadgeRead(TimestampedRead):
    name: str
    description: Optional[str] = None
    icon_url: Optional[str] = None
    trigger_key: Optional[str] = None


class UserBadgeRead(ORMBase):
    """Shown on public portfolio pages — badge details flattened in, no raw IDs needed by the client."""
    badge: BadgeRead
    earned_at: Optional[datetime] = None
