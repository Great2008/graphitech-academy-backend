"""
app/services/admin_service.py

Aggregation queries for the admin management suite. Kept as plain COUNT/
JOIN queries rather than loading full ORM objects where possible, since
this runs on every dashboard page load.
"""

from typing import List
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.models.base import UserRole, CourseStatus, EnrollmentStatus, CapstoneStatus
from app.models.learning import Course, Lesson
from app.models.enrollment import Enrollment, Progress
from app.models.certificate import Certificate
from app.models.assessment import CapstoneSubmission
from app.schemas.admin import DashboardStats, StudentListItem, StudentDetail, EnrollmentProgress


def get_dashboard_stats(db: Session) -> DashboardStats:
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_students = (
        db.query(func.count(User.id)).filter(User.role == UserRole.STUDENT).scalar() or 0
    )
    total_staff = total_users - total_students

    total_courses_published = (
        db.query(func.count(Course.id))
        .filter(Course.status == CourseStatus.PUBLISHED, Course.is_latest_version.is_(True))
        .scalar()
        or 0
    )
    total_courses_draft = (
        db.query(func.count(Course.id))
        .filter(Course.status == CourseStatus.DRAFT, Course.is_latest_version.is_(True))
        .scalar()
        or 0
    )

    total_enrollments = db.query(func.count(Enrollment.id)).scalar() or 0
    total_completed_enrollments = (
        db.query(func.count(Enrollment.id))
        .filter(Enrollment.status == EnrollmentStatus.COMPLETED)
        .scalar()
        or 0
    )

    total_certificates_issued = db.query(func.count(Certificate.id)).scalar() or 0

    pending_capstone_reviews = (
        db.query(func.count(CapstoneSubmission.id))
        .filter(CapstoneSubmission.status.in_([CapstoneStatus.SUBMITTED, CapstoneStatus.UNDER_REVIEW]))
        .scalar()
        or 0
    )

    return DashboardStats(
        total_users=total_users,
        total_students=total_students,
        total_staff=total_staff,
        total_courses_published=total_courses_published,
        total_courses_draft=total_courses_draft,
        total_enrollments=total_enrollments,
        total_completed_enrollments=total_completed_enrollments,
        total_certificates_issued=total_certificates_issued,
        pending_capstone_reviews=pending_capstone_reviews,
    )


def list_students(db: Session) -> List[StudentListItem]:
    students = db.query(User).filter(User.role == UserRole.STUDENT).order_by(User.created_at.desc()).all()

    results = []
    for student in students:
        enrollment_count = (
            db.query(func.count(Enrollment.id)).filter(Enrollment.user_id == student.id).scalar() or 0
        )
        completed_count = (
            db.query(func.count(Enrollment.id))
            .filter(Enrollment.user_id == student.id, Enrollment.status == EnrollmentStatus.COMPLETED)
            .scalar()
            or 0
        )
        certificate_count = (
            db.query(func.count(Certificate.id)).filter(Certificate.user_id == student.id).scalar() or 0
        )
        results.append(
            StudentListItem(
                id=student.id,
                username=student.username,
                display_name=student.display_name,
                email=student.email,
                enrollment_count=enrollment_count,
                completed_count=completed_count,
                certificate_count=certificate_count,
            )
        )
    return results


def get_student_detail(db: Session, user_id: UUID) -> StudentDetail:
    student = db.query(User).filter(User.id == user_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    enrollments = db.query(Enrollment).filter(Enrollment.user_id == user_id).all()

    enrollment_progress = []
    for enrollment in enrollments:
        course = db.query(Course).filter(Course.id == enrollment.course_id).first()
        total_lessons = db.query(func.count(Lesson.id)).filter(Lesson.course_id == course.id).scalar() or 0
        completed_lessons = (
            db.query(func.count(Progress.id))
            .filter(Progress.enrollment_id == enrollment.id, Progress.is_completed.is_(True))
            .scalar()
            or 0
        )
        progress_percent = int((completed_lessons / total_lessons) * 100) if total_lessons > 0 else 0

        enrollment_progress.append(
            EnrollmentProgress(
                course_id=course.id,
                course_title=course.title,
                status=enrollment.status.value,
                is_eligible_for_certificate=enrollment.is_eligible_for_certificate,
                total_lessons=total_lessons,
                completed_lessons=completed_lessons,
                progress_percent=progress_percent,
            )
        )

    return StudentDetail(
        id=student.id,
        username=student.username,
        display_name=student.display_name,
        email=student.email,
        role=student.role.value,
        enrollments=enrollment_progress,
    )
