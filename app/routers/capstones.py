"""
app/routers/capstones.py

Student (authenticated):
  POST /api/capstones                    (submit)
  GET  /api/capstones/{capstone_id}       (view own or staff view any)

Reviewer/Instructor/Admin only:
  GET  /api/capstones                     (list pending, optional ?course_id=)
  POST /api/capstones/{capstone_id}/review
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.base import UserRole
from app.models.user import User
from app.schemas.assessment import CapstoneSubmissionCreate, CapstoneSubmissionRead, CapstoneReviewDecision
from app.services import capstone_service

router = APIRouter()

REVIEW_ROLES = (UserRole.REVIEWER, UserRole.INSTRUCTOR, UserRole.ADMIN, UserRole.SUPER_ADMIN)


@router.post("/capstones", response_model=CapstoneSubmissionRead, status_code=201)
def submit_capstone(
    submission_in: CapstoneSubmissionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return capstone_service.submit_capstone(db, current_user.id, submission_in)


@router.get("/capstones/{capstone_id}", response_model=CapstoneSubmissionRead)
def get_capstone(
    capstone_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    submission = capstone_service.get_capstone(db, capstone_id)
    is_owner = submission.user_id == current_user.id
    is_staff = current_user.role in REVIEW_ROLES
    if not (is_owner or is_staff):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this submission")
    return submission


@router.get(
    "/capstones",
    response_model=List[CapstoneSubmissionRead],
    dependencies=[Depends(require_role(*REVIEW_ROLES))],
)
def list_pending_capstones(
    course_id: Optional[UUID] = Query(default=None),
    db: Session = Depends(get_db),
):
    return capstone_service.list_pending_capstones(db, course_id)


@router.post(
    "/capstones/{capstone_id}/review",
    response_model=CapstoneSubmissionRead,
    dependencies=[Depends(require_role(*REVIEW_ROLES))],
)
def review_capstone(
    capstone_id: UUID,
    decision: CapstoneReviewDecision,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return capstone_service.review_capstone(db, capstone_id, current_user.id, decision)
