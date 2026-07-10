"""
app/routers/admin.py

Staff-only (Instructor/Admin/Super Admin):
  GET /api/admin/dashboard
  GET /api/admin/students
  GET /api/admin/students/{user_id}
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import require_role
from app.models.base import UserRole
from app.schemas.admin import DashboardStats, StudentListItem, StudentDetail
from app.services import admin_service

router = APIRouter()

STAFF_ROLES = (UserRole.INSTRUCTOR, UserRole.ADMIN, UserRole.SUPER_ADMIN)


@router.get("/admin/dashboard", response_model=DashboardStats, dependencies=[Depends(require_role(*STAFF_ROLES))])
def dashboard_stats(db: Session = Depends(get_db)):
    return admin_service.get_dashboard_stats(db)


@router.get("/admin/students", response_model=List[StudentListItem], dependencies=[Depends(require_role(*STAFF_ROLES))])
def list_students(db: Session = Depends(get_db)):
    return admin_service.list_students(db)


@router.get(
    "/admin/students/{user_id}",
    response_model=StudentDetail,
    dependencies=[Depends(require_role(*STAFF_ROLES))],
)
def student_detail(user_id: UUID, db: Session = Depends(get_db)):
    return admin_service.get_student_detail(db, user_id)
