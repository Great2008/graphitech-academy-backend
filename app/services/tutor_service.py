"""
app/services/tutor_service.py

Handles the free-tier rate limit, premium bypass, and TutorUsage logging
around the raw Groq call in ai_service.chat_with_tutor().

Rate limit is a simple "count of TutorUsage rows created today" check —
good enough for v1 without needing a separate counter/cache table.
"""

from datetime import datetime, timezone, time
from uuid import UUID

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.models.ai_tutor import TutorUsage
from app.models.user import User
from app.schemas.ai_tutor import TutorChatRequest, TutorChatResponse
from app.services import ai_service


def is_premium(user: User) -> bool:
    return bool(user.tutor_premium_until and user.tutor_premium_until > datetime.now(timezone.utc))


def _today_usage_count(db: Session, user_id: UUID) -> int:
    start_of_day = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
    return (
        db.query(TutorUsage)
        .filter(TutorUsage.user_id == user_id, TutorUsage.created_at >= start_of_day)
        .count()
    )


def chat(db: Session, user: User, request_in: TutorChatRequest) -> TutorChatResponse:
    premium = is_premium(user)
    used_today = _today_usage_count(db, user.id)

    if not premium and used_today >= settings.TUTOR_FREE_DAILY_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"You've used all {settings.TUTOR_FREE_DAILY_LIMIT} free AI tutor questions for today. "
                "Upgrade to premium for unlimited access, or come back tomorrow."
            ),
        )

    result = ai_service.chat_with_tutor(request_in.message, is_premium=premium)

    usage = TutorUsage(
        user_id=user.id,
        course_id=request_in.course_id,
        lesson_id=request_in.lesson_id,
        prompt_char_count=len(request_in.message),
        response_char_count=len(result["reply"]),
        model_used=result["model_used"],
        low_confidence_flag=result["low_confidence_flag"],
        flagged_for_plagiarism_risk=result["plagiarism_nudge"] is not None,
        is_premium_request=premium,
    )
    db.add(usage)
    db.commit()

    remaining = None if premium else max(0, settings.TUTOR_FREE_DAILY_LIMIT - (used_today + 1))

    return TutorChatResponse(
        reply=result["reply"],
        low_confidence_flag=result["low_confidence_flag"],
        plagiarism_nudge=result["plagiarism_nudge"],
        remaining_free_requests_today=remaining,
        is_premium_response=premium,
    )
