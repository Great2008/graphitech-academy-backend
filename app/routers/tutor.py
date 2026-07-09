"""
app/routers/tutor.py

Student (authenticated):
  POST /api/tutor/chat
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.ai_tutor import TutorChatRequest, TutorChatResponse
from app.services import tutor_service

router = APIRouter()


@router.post("/tutor/chat", response_model=TutorChatResponse)
def chat_with_tutor(
    request_in: TutorChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return tutor_service.chat(db, current_user, request_in)
