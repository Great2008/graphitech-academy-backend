"""
app/schemas/enrollment.py
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.schemas.base import ORMBase, TimestampedRead, EnrollmentStatus


class EnrollmentCreate(BaseModel):
    course_id: UUID


class EnrollmentRead(TimestampedRead):
    user_id: UUID
    course_id: UUID
    status: EnrollmentStatus
    is_eligible_for_certificate: bool


class ProgressUpdate(BaseModel):
    lesson_id: UUID
    is_completed: bool
    time_spent_seconds: Optional[int] = None


class ProgressRead(TimestampedRead):
    enrollment_id: UUID
    lesson_id: UUID
    is_completed: bool
    time_spent_seconds: Optional[int] = None
