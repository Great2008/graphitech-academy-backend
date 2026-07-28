"""
app/routers/admin.py

Staff-only (Instructor/Admin/Super Admin):
  GET /api/admin/dashboard
  GET /api/admin/students
  GET /api/admin/students/{user_id}
  GET /api/admin/certificates
  GET /api/admin/payments

Admin/Super Admin only:
  GET   /api/admin/users
  PATCH /api/admin/users/{user_id}/role
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import require_role, get_current_user
from app.models.base import UserRole
from app.models.user import User
from app.schemas.admin import DashboardStats, StudentListItem, StudentDetail
from app.schemas.user import UserRead, UserRoleUpdate
from app.schemas.certificate import CertificateRead
from app.schemas.payment import PaymentRead
from app.services import admin_service

router = APIRouter()

STAFF_ROLES = (UserRole.INSTRUCTOR, UserRole.ADMIN, UserRole.SUPER_ADMIN)
ADMIN_ROLES = (UserRole.ADMIN, UserRole.SUPER_ADMIN)


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


@router.get("/admin/users", response_model=List[UserRead], dependencies=[Depends(require_role(*ADMIN_ROLES))])
def list_all_users(db: Session = Depends(get_db)):
    return admin_service.list_all_users(db)


@router.patch(
    "/admin/users/{user_id}/role",
    response_model=UserRead,
    dependencies=[Depends(require_role(*ADMIN_ROLES))],
)
def update_user_role(
    user_id: UUID,
    role_update: UserRoleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return admin_service.update_user_role(db, user_id, role_update.role, current_user)


@router.get(
    "/admin/certificates",
    response_model=List[CertificateRead],
    dependencies=[Depends(require_role(*STAFF_ROLES))],
)
def list_all_certificates(db: Session = Depends(get_db)):
    return admin_service.list_all_certificates(db)


@router.get(
    "/admin/payments",
    response_model=List[PaymentRead],
    dependencies=[Depends(require_role(*STAFF_ROLES))],
)
def list_all_payments(db: Session = Depends(get_db)):
    return admin_service.list_all_payments(db)
