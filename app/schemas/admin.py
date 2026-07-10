"""
app/schemas/admin.py

Schemas for the admin management suite — dashboard stats, student roster,
and per-student progress detail. Kept separate from analytics.py's
grant-readiness schemas since this serves the day-to-day admin UI, not
funder reporting.
"""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.schemas.base import ORMBase


class DashboardStats(BaseModel):
    total_users: int
    total_students: int
    total_staff: int
    total_courses_published: int
    total_courses_draft: int
    total_enrollments: int
    total_completed_enrollments: int
    total_certificates_issued: int
    pending_capstone_reviews: int


class StudentListItem(BaseModel):
    id: UUID
    username: str
    display_name: Optional[str] = None
    email: str
    enrollment_count: int
    completed_count: int
    certificate_count: int


class EnrollmentProgress(BaseModel):
    course_id: UUID
    course_title: str
    status: str
    is_eligible_for_certificate: bool
    total_lessons: int
    completed_lessons: int
    progress_percent: int


class StudentDetail(BaseModel):
    id: UUID
    username: str
    display_name: Optional[str] = None
    email: str
    role: str
    enrollments: List[EnrollmentProgress]
