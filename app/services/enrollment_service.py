"""
app/services/enrollment_service.py

Handles enrolling a user in a course, recording lesson progress, and
computing certificate eligibility.

Completion is server-verified, never a trusted client flag:
  - Lessons WITHOUT a quiz: complete once enough time has been spent
    viewing them (see ping_lesson_progress / _required_seconds).
  - Lessons WITH a quiz: complete ONLY by passing that quiz — see
    quiz_service.submit_quiz_attempt, which calls
    mark_lesson_complete_via_quiz below. No other path can complete
    a quiz-gated lesson.

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


def _get_or_create_progress(db: Session, enrollment_id: UUID, lesson_id: UUID) -> Progress:
    progress = (
        db.query(Progress)
        .filter(Progress.enrollment_id == enrollment_id, Progress.lesson_id == lesson_id)
        .first()
    )
    if not progress:
        progress = Progress(enrollment_id=enrollment_id, lesson_id=lesson_id)
        db.add(progress)
    return progress


def _required_seconds(lesson: Lesson) -> int:
    """
    How long a student must spend on a no-quiz lesson before it auto-completes.
    60% of the lesson's estimated reading time, floor of 15s so a very short
    lesson isn't effectively unblockable; falls back to a flat 45s if the
    lesson has no estimated_minutes set.
    """
    if lesson.estimated_minutes:
        return max(15, int(lesson.estimated_minutes * 60 * 0.6))
    return 45


def ping_lesson_progress(
    db: Session,
    user_id: UUID,
    course_id: UUID,
    lesson_id: UUID,
    time_spent_seconds: Optional[int] = None,
) -> Progress:
    """
    Called periodically (e.g. every 15s) while a student is actively viewing
    a lesson. Accumulates time. For lessons without a quiz, this is the only
    thing that can flip is_completed — once accumulated time clears the
    threshold, the server marks it complete itself. For lessons with a quiz,
    this only accumulates time; completion still requires passing the quiz.
    """
    enrollment = get_enrollment(db, user_id, course_id)
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id, Lesson.course_id == course_id).first()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found on this course")

    progress = _get_or_create_progress(db, enrollment.id, lesson_id)

    if time_spent_seconds:
        progress.time_spent_seconds = (progress.time_spent_seconds or 0) + max(0, time_spent_seconds)

    if not lesson.has_quiz and not progress.is_completed:
        if (progress.time_spent_seconds or 0) >= _required_seconds(lesson):
            progress.is_completed = True
            progress.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(progress)

    _recompute_completion(db, enrollment)
    return progress


def mark_lesson_complete_via_quiz(db: Session, user_id: UUID, course_id: UUID, lesson_id: UUID) -> Progress:
    """Called only from quiz_service.submit_quiz_attempt after a genuine pass."""
    enrollment = get_enrollment(db, user_id, course_id)
    progress = _get_or_create_progress(db, enrollment.id, lesson_id)

    progress.is_completed = True
    progress.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(progress)

    _recompute_completion(db, enrollment)
    return progress


def _recompute_completion(db: Session, enrollment: Enrollment) -> None:
    """
    Checks whether all lessons in the course are complete. If the course
    doesn't require a capstone, certificate eligibility flips on immediately.
    If it does require a capstone, eligibility only flips on if a capstone
    was already APPROVED (handles the case where capstone review happened
    before the last lesson was marked complete — the more common case,
    where lessons finish first, is handled in capstone_service instead).
    """
    from app.models.assessment import CapstoneSubmission
    from app.models.base import CapstoneStatus

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

        became_eligible = False
        if not course.requires_capstone:
            if not enrollment.is_eligible_for_certificate:
                became_eligible = True
            enrollment.is_eligible_for_certificate = True
        else:
            approved_capstone = (
                db.query(CapstoneSubmission)
                .filter(
                    CapstoneSubmission.user_id == enrollment.user_id,
                    CapstoneSubmission.course_id == enrollment.course_id,
                    CapstoneSubmission.status == CapstoneStatus.APPROVED,
                )
                .first()
            )
            if approved_capstone:
                if not enrollment.is_eligible_for_certificate:
                    became_eligible = True
                enrollment.is_eligible_for_certificate = True

        db.commit()

        if became_eligible:
            from app.services import certificate_service
            certificate_service.try_auto_issue_free_certificate(db, enrollment.user_id, enrollment.course_id)
