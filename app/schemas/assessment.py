"""
app/schemas/assessment.py
"""

from typing import Optional, List, Any, Dict
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import ORMBase, TimestampedRead, QuizAttemptStatus, CapstoneStatus


# --- Quiz ---

class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    correct_index: int


class QuizCreate(BaseModel):
    lesson_id: UUID
    title: str
    pass_mark_percent: int = Field(default=70, ge=0, le=100)
    questions: List[QuizQuestion]


class QuizRead(TimestampedRead):
    lesson_id: UUID
    title: str
    pass_mark_percent: int
    questions: List[QuizQuestion]


class QuizPublicQuestion(BaseModel):
    """Question shown to students — correct_index withheld until submission."""
    question: str
    options: List[str]


class QuizPublicRead(ORMBase):
    id: UUID
    title: str
    questions: List[QuizPublicQuestion]


# --- Quiz Attempt ---

class QuizAttemptSubmit(BaseModel):
    quiz_id: UUID
    answers: Dict[str, int]  # question index (as string key) -> selected option index


class QuizAttemptRead(TimestampedRead):
    quiz_id: UUID
    user_id: UUID
    score_percent: int
    status: QuizAttemptStatus
    submitted_at: Optional[str] = None


# --- Capstone ---

class CapstoneSubmissionCreate(BaseModel):
    course_id: UUID
    title: str
    description: Optional[str] = None
    repo_url: Optional[str] = None
    live_url: Optional[str] = None


class CapstoneReviewDecision(BaseModel):
    """Instructor/Reviewer only."""
    status: CapstoneStatus = Field(..., description="Must be APPROVED or REJECTED")
    reviewer_feedback: Optional[str] = None


class CapstoneSubmissionRead(TimestampedRead):
    user_id: UUID
    course_id: UUID
    title: str
    description: Optional[str] = None
    repo_url: Optional[str] = None
    live_url: Optional[str] = None
    status: CapstoneStatus
    reviewer_id: Optional[UUID] = None
    reviewer_feedback: Optional[str] = None
    auto_grade_result: Optional[Dict[str, Any]] = None
