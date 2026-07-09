"""
app/routers/courses.py

Public:
  GET  /api/learning-paths
  GET  /api/courses
  GET  /api/courses/{slug}

Student (authenticated):
  POST /api/courses/{course_id}/enroll
  POST /api/courses/{course_id}/progress

Instructor/Admin only:
  POST  /api/courses                          (create draft course)
  POST  /api/courses/{course_id}/lessons       (add lesson to draft course)
  PATCH /api/courses/{course_id}               (edit draft course metadata)
  POST  /api/courses/{course_id}/publish       (draft -> published)
  POST  /api/courses/{course_id}/new-version   (published -> new draft version)
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.base import UserRole
from app.models.user import User
from app.schemas.learning import (
    LearningPathRead, CourseRead, CourseWithLessons, CourseCreate, CourseUpdate,
    CourseAIDraftRequest, LessonCreate, LessonUpdate, LessonRead,
)
from app.schemas.enrollment import EnrollmentRead, ProgressUpdate, ProgressRead
from app.services import course_service, enrollment_service, ai_service

router = APIRouter()

STAFF_ROLES = (UserRole.INSTRUCTOR, UserRole.ADMIN, UserRole.SUPER_ADMIN)


# --- Public browse routes ---

@router.get("/learning-paths", response_model=List[LearningPathRead])
def list_learning_paths(db: Session = Depends(get_db)):
    return course_service.get_learning_paths(db)


@router.get("/courses", response_model=List[CourseRead])
def list_courses(
    learning_path_id: Optional[UUID] = Query(default=None),
    db: Session = Depends(get_db),
):
    return course_service.list_published_courses(db, learning_path_id)


@router.get("/courses/{slug}", response_model=CourseWithLessons)
def get_course(slug: str, db: Session = Depends(get_db)):
    course = course_service.get_course_by_slug(db, slug)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return course


# --- Student routes ---

@router.post("/courses/{course_id}/enroll", response_model=EnrollmentRead, status_code=201)
def enroll(course_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return enrollment_service.enroll_user(db, current_user.id, course_id)


@router.post("/courses/{course_id}/progress", response_model=ProgressRead)
def update_progress(
    course_id: UUID,
    progress_in: ProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return enrollment_service.mark_lesson_progress(
        db,
        user_id=current_user.id,
        course_id=course_id,
        lesson_id=progress_in.lesson_id,
        is_completed=progress_in.is_completed,
        time_spent_seconds=progress_in.time_spent_seconds,
    )


# --- Instructor/Admin routes ---

@router.post(
    "/courses",
    response_model=CourseRead,
    status_code=201,
    dependencies=[Depends(require_role(*STAFF_ROLES))],
)
def create_course(course_in: CourseCreate, db: Session = Depends(get_db)):
    return course_service.create_course(db, course_in)


@router.post(
    "/courses/ai-draft",
    response_model=CourseWithLessons,
    status_code=201,
    dependencies=[Depends(require_role(*STAFF_ROLES))],
)
def ai_draft_course(draft_request: CourseAIDraftRequest, db: Session = Depends(get_db)):
    """
    Drafts a full course (title, description, lessons, optional quizzes)
    via Groq, then saves it as a DRAFT course — nothing is published.
    Review and edit the result, then call POST /courses/{id}/publish
    when it's ready for students.
    """
    draft = ai_service.draft_course_with_ai(draft_request)
    return course_service.create_course_from_ai_draft(db, draft, draft_request)


@router.post(
    "/courses/{course_id}/lessons",
    response_model=LessonRead,
    status_code=201,
    dependencies=[Depends(require_role(*STAFF_ROLES))],
)
def add_lesson(course_id: UUID, lesson_in: LessonCreate, db: Session = Depends(get_db)):
    return course_service.add_lesson(db, course_id, lesson_in)


@router.patch(
    "/courses/{course_id}/lessons/{lesson_id}",
    response_model=LessonRead,
    dependencies=[Depends(require_role(*STAFF_ROLES))],
)
def update_lesson(course_id: UUID, lesson_id: UUID, updates: LessonUpdate, db: Session = Depends(get_db)):
    return course_service.update_lesson(db, course_id, lesson_id, updates)


@router.delete(
    "/courses/{course_id}/lessons/{lesson_id}",
    status_code=204,
    dependencies=[Depends(require_role(*STAFF_ROLES))],
)
def delete_lesson(course_id: UUID, lesson_id: UUID, db: Session = Depends(get_db)):
    course_service.delete_lesson(db, course_id, lesson_id)
    return None


@router.patch(
    "/courses/{course_id}",
    response_model=CourseRead,
    dependencies=[Depends(require_role(*STAFF_ROLES))],
)
def update_course(course_id: UUID, updates: CourseUpdate, db: Session = Depends(get_db)):
    return course_service.update_course_metadata(db, course_id, updates)


@router.post(
    "/courses/{course_id}/publish",
    response_model=CourseRead,
    dependencies=[Depends(require_role(*STAFF_ROLES))],
)
def publish_course(course_id: UUID, db: Session = Depends(get_db)):
    return course_service.publish_course(db, course_id)


@router.post(
    "/courses/{course_id}/new-version",
    response_model=CourseRead,
    status_code=201,
    dependencies=[Depends(require_role(*STAFF_ROLES))],
)
def new_course_version(course_id: UUID, db: Session = Depends(get_db)):
    return course_service.create_new_version(db, course_id)
