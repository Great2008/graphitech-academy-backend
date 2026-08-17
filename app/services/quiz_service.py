"""
app/services/quiz_service.py

A lesson with has_quiz=True can ONLY be marked complete by passing this
quiz -- that's what makes "mark complete" mean something real instead of a
trusted client-supplied flag. See enrollment_service.py for the other half
(time-gated completion for lessons without a quiz).
"""

from datetime import datetime, timezone
from typing import Dict
from uuid import UUID

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.assessment import Quiz, QuizAttempt
from app.models.learning import Lesson
from app.models.base import QuizAttemptStatus
from app.schemas.assessment import QuizPublicRead, QuizPublicQuestion, QuizAttemptRead
from app.services import enrollment_service


def get_quiz_for_lesson(db: Session, lesson_id: UUID) -> QuizPublicRead:
    quiz = db.query(Quiz).filter(Quiz.lesson_id == lesson_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This lesson has no quiz")
    return QuizPublicRead(
        id=quiz.id,
        title=quiz.title,
        questions=[
            QuizPublicQuestion(question=q["question"], options=q["options"])
            for q in quiz.questions
        ],
    )


def submit_quiz_attempt(
    db: Session,
    user_id: UUID,
    quiz_id: UUID,
    answers: Dict[str, int],
) -> QuizAttemptRead:
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")

    lesson = db.query(Lesson).filter(Lesson.id == quiz.lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson for this quiz not found")

    total_questions = len(quiz.questions)
    correct_count = 0
    for index, question in enumerate(quiz.questions):
        selected = answers.get(str(index))
        if selected is not None and selected == question.get("correct_index"):
            correct_count += 1

    score_percent = int((correct_count / total_questions) * 100) if total_questions else 0
    passed = score_percent >= quiz.pass_mark_percent

    attempt = QuizAttempt(
        quiz_id=quiz.id,
        user_id=user_id,
        score_percent=score_percent,
        status=QuizAttemptStatus.PASSED if passed else QuizAttemptStatus.FAILED,
        answers=answers,
        submitted_at=datetime.now(timezone.utc),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    if passed:
        enrollment_service.mark_lesson_complete_via_quiz(db, user_id, lesson.course_id, lesson.id)

    return QuizAttemptRead.model_validate(attempt)
