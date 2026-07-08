"""
app/services/enrollment_service.py

Handles enrolling a user in a course, recording lesson progress, and
computing certificate eligibility.

Certificate eligibility rule (Enrollment.is_eligible_for_certificate):
  - All lessons marked complete, AND
  - If course.requires_capstone: an APPROVED CapstoneSubmission exists
    (checked in the capstone review flow, not here — this service only
    handles the lesson-progress half of eligibility)
"""

from typing import Optional
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.enrollment import Enrollment, Progress
from app.models.learning import Course, Lesson
from app.models.base import EnrollmentStatus


def enroll_user(db: Session, user_id: UUID, course_id: UUID) -> Enrollment:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    existing = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
        .first()
    )
    if existing:
        return existing

    enrollment = Enrollment(
        user_id=user_id,
        course_id=course_id,
        status=EnrollmentStatus.ACTIVE,
        enrolled_at=datetime.now(timezone.utc),
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


def get_enrollment(db: Session, user_id: UUID, course_id: UUID) -> Enrollment:
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not enrolled in this course")
    return enrollment


def mark_lesson_progress(
    db: Session,
    user_id: UUID,
    course_id: UUID,
    lesson_id: UUID,
    is_completed: bool,
    time_spent_seconds: Optional[int] = None,
) -> Progress:
    enrollment = get_enrollment(db, user_id, course_id)

    progress = (
        db.query(Progress)
        .filter(Progress.enrollment_id == enrollment.id, Progress.lesson_id == lesson_id)
        .first()
    )
    if not progress:
        progress = Progress(enrollment_id=enrollment.id, lesson_id=lesson_id)
        db.add(progress)

    progress.is_completed = is_completed
    if time_spent_seconds is not None:
        progress.time_spent_seconds = (progress.time_spent_seconds or 0) + time_spent_seconds
    if is_completed:
        progress.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(progress)

    _recompute_completion(db, enrollment)
    return progress


def _recompute_completion(db: Session, enrollment: Enrollment) -> None:
    """
    Checks whether all lessons in the course are complete, and — if the
    course doesn't require a capstone — flips certificate eligibility on.
    (If it does require a capstone, eligibility is finalized in the
    capstone review flow instead.)
    """
    course = db.query(Course).filter(Course.id == enrollment.course_id).first()
    total_lessons = db.query(Lesson).filter(Lesson.course_id == course.id).count()
    completed_lessons = (
        db.query(Progress)
        .filter(Progress.enrollment_id == enrollment.id, Progress.is_completed.is_(True))
        .count()
    )

    if total_lessons > 0 and completed_lessons >= total_lessons:
        enrollment.status = EnrollmentStatus.COMPLETED
        enrollment.completed_at = enrollment.completed_at or datetime.now(timezone.utc)
        if not course.requires_capstone:
            enrollment.is_eligible_for_certificate = True
        db.commit()
