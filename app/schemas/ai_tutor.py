"""
app/schemas/ai_tutor.py

TutorChatResponse carries the safety fields the frontend needs to render
disclaimers/nudges without the client having to infer anything.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.schemas.base import ORMBase, TimestampedRead


class TutorChatRequest(BaseModel):
    message: str
    course_id: Optional[UUID] = None
    lesson_id: Optional[UUID] = None


class TutorChatResponse(BaseModel):
    reply: str
    low_confidence_flag: bool = False
    plagiarism_nudge: Optional[str] = None  # e.g. "Try explaining your approach first — I can check your reasoning."
    remaining_free_requests_today: Optional[int] = None
    is_premium_response: bool = False


class TutorUsageRead(TimestampedRead):
    user_id: UUID
    course_id: Optional[UUID] = None
    lesson_id: Optional[UUID] = None
    model_used: Optional[str] = None
    low_confidence_flag: bool
    flagged_for_plagiarism_risk: bool
    is_premium_request: bool
