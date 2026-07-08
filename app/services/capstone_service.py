"""
app/services/capstone_service.py

Handles capstone submission and review. Approval is the final piece of
certificate eligibility for courses where requires_capstone=True — once
approved, this checks that all lessons are also complete and, if so,
flips Enrollment.is_eligible_for_certificate.
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.assessment import CapstoneSubmission
from app.models.enrollment import Enrollment, Progress
from app.models.learning import Course, Lesson
from app.models.base import CapstoneStatus, EnrollmentStatus
from app.schemas.assessment import CapstoneSubmissionCreate, CapstoneReviewDecision


def submit_capstone(db: Session, user_id: UUID, submission_in: CapstoneSubmissionCreate) -> CapstoneSubmission:
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user_id, Enrollment.course_id == submission_in.course_id)
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not enrolled in this course")

    # Only one active (non-rejected) submission per user/course at a time.
    existing = (
        db.query(CapstoneSubmission)
        .filter(
            CapstoneSubmission.user_id == user_id,
            CapstoneSubmission.course_id == submission_in.course_id,
            CapstoneSubmission.status != CapstoneStatus.REJECTED,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A capstone submission already exists for this course. Wait for review or resubmit after rejection.",
        )

    submission = CapstoneSubmission(
        user_id=user_id,
        course_id=submission_in.course_id,
        title=submission_in.title,
        description=submission_in.description,
        repo_url=submission_in.repo_url,
        live_url=submission_in.live_url,
        status=CapstoneStatus.SUBMITTED,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


def list_pending_capstones(db: Session, course_id: Optional[UUID] = None) -> List[CapstoneSubmission]:
    query = db.query(CapstoneSubmission).filter(
        CapstoneSubmission.status.in_([CapstoneStatus.SUBMITTED, CapstoneStatus.UNDER_REVIEW])
    )
    if course_id:
        query = query.filter(CapstoneSubmission.course_id == course_id)
    return query.order_by(CapstoneSubmission.created_at).all()


def get_capstone(db: Session, capstone_id: UUID) -> CapstoneSubmission:
    submission = db.query(CapstoneSubmission).filter(CapstoneSubmission.id == capstone_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capstone submission not found")
    return submission


def review_capstone(
    db: Session,
    capstone_id: UUID,
    reviewer_id: UUID,
    decision: CapstoneReviewDecision,
) -> CapstoneSubmission:
    if decision.status not in (CapstoneStatus.APPROVED, CapstoneStatus.REJECTED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Review decision must be APPROVED or REJECTED",
        )

    submission = get_capstone(db, capstone_id)
    submission.status = decision.status
    submission.reviewer_id = reviewer_id
    submission.reviewer_feedback = decision.reviewer_feedback
    submission.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(submission)

    if decision.status == CapstoneStatus.APPROVED:
        _finalize_certificate_eligibility(db, submission.user_id, submission.course_id)

    return submission


def _finalize_certificate_eligibility(db: Session, user_id: UUID, course_id: UUID) -> None:
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
        .first()
    )
    if not enrollment:
        return

    course = db.query(Course).filter(Course.id == course_id).first()
    total_lessons = db.query(Lesson).filter(Lesson.course_id == course.id).count()
    completed_lessons = (
        db.query(Progress)
        .filter(Progress.enrollment_id == enrollment.id, Progress.is_completed.is_(True))
        .count()
    )

    if total_lessons > 0 and completed_lessons >= total_lessons:
        enrollment.is_eligible_for_certificate = True
        enrollment.status = EnrollmentStatus.COMPLETED
        enrollment.completed_at = enrollment.completed_at or datetime.now(timezone.utc)
        db.commit()
    # If lessons aren't all complete yet, eligibility will be finalized
    # automatically once the last lesson is marked complete — see
    # enrollment_service._recompute_completion, which checks for an
    # approved capstone at that point.
