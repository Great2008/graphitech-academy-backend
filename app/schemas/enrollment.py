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


class LessonProgressPing(BaseModel):
    """
    Sent periodically while a student is actively viewing a lesson.
    Deliberately has no is_completed field — completion is always computed
    server-side (time threshold for no-quiz lessons, quiz pass otherwise),
    never trusted from the client.
    """
    lesson_id: UUID
    time_spent_seconds: Optional[int] = None


class ProgressRead(TimestampedRead):
    enrollment_id: UUID
    lesson_id: UUID
    is_completed: bool
    time_spent_seconds: Optional[int] = None
