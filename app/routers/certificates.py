"""
app/routers/certificates.py

Public (no auth — this is the whole point):
  GET /api/verify/{certificate_number}
  GET /api/certificates/{certificate_number}/download

Student (authenticated):
  GET /api/certificates/me

Admin/Super Admin only:
  POST /api/certificates/{certificate_id}/revoke
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.base import UserRole
from app.models.user import User
from app.schemas.certificate import CertificateRead, CertificateVerifyPublic, CertificateRevoke
from app.services import certificate_service

router = APIRouter()


@router.post("/certificates/claim/{course_id}", response_model=CertificateRead)
def claim_free_certificate(
    course_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return certificate_service.claim_free_certificate(db, current_user.id, course_id)


@router.get("/verify/{certificate_number}", response_model=CertificateVerifyPublic)
def verify_certificate(certificate_number: str, db: Session = Depends(get_db)):
    return certificate_service.verify_certificate(db, certificate_number)


@router.get("/certificates/{certificate_number}/download")
def download_certificate(certificate_number: str, db: Session = Depends(get_db)):
    """
    Public, same access level as /verify — anyone holding a certificate
    number can download the PDF. Generated fresh on every request rather
    than served from storage, so this works even if the async asset
    upload at issuance time failed or storage isn't configured.
    """
    certificate = certificate_service.verify_certificate(db, certificate_number)

    from app.services import certificate_pdf_service
    pdf_bytes = certificate_pdf_service.render_certificate_pdf_bytes(certificate)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{certificate_number}.pdf"'},
    )


@router.get("/certificates/me", response_model=List[CertificateRead])
def get_my_certificates(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return certificate_service.get_user_certificates(db, current_user.id)


@router.post(
    "/certificates/{certificate_id}/regenerate-assets",
    response_model=CertificateRead,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))],
)
def regenerate_certificate_assets(certificate_id: UUID, db: Session = Depends(get_db)):
    return certificate_service.regenerate_certificate_assets(db, certificate_id)


@router.post(
    "/certificates/{certificate_id}/revoke",
    response_model=CertificateRead,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))],
)
def revoke_certificate(certificate_id: UUID, revoke_in: CertificateRevoke, db: Session = Depends(get_db)):
    return certificate_service.revoke_certificate(db, certificate_id, revoke_in.reason)
