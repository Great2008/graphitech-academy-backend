"""
app/services/certificate_service.py

Issues certificates once payment is confirmed. certificate_number format:
  GTA-{year}-{course_code}-{6-digit sequence}
  e.g. GTA-2026-WD-000123

course_code is derived from the course slug (first letters of each word,
uppercased) — simple and stable enough for v1; can be made explicit on
the Course model later if needed.

PDF/QR generation is stubbed with clear TODOs for wiring to WeasyPrint +
qrcode + Supabase storage — the surrounding logic (numbering, snapshot
fields, eligibility checks, verification) is what actually matters for
correctness and is fully implemented.
"""

from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from app.models.certificate import Certificate
from app.models.payment import Payment
from app.models.enrollment import Enrollment
from app.models.learning import Course
from app.models.user import User
from app.models.base import CertificateStatus


def _generate_course_code(course_slug: str) -> str:
    parts = [p for p in course_slug.replace("_", "-").split("-") if p]
    initials = "".join(p[0] for p in parts[:3]).upper()
    return initials or "GEN"


def _next_sequence_number(db: Session, year: int) -> int:
    prefix = f"GTA-{year}-"
    count = (
        db.query(func.count(Certificate.id))
        .filter(Certificate.certificate_number.like(f"{prefix}%"))
        .scalar()
    )
    return (count or 0) + 1


def issue_certificate(db: Session, payment: Payment) -> Certificate:
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == payment.user_id, Enrollment.course_id == payment.course_id)
        .first()
    )
    if not enrollment or not enrollment.is_eligible_for_certificate:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Enrollment is not eligible for a certificate — payment cannot be fulfilled",
        )

    existing = db.query(Certificate).filter(Certificate.payment_id == payment.id).first()
    if existing:
        return existing

    course = db.query(Course).filter(Course.id == payment.course_id).first()
    user = db.query(User).filter(User.id == payment.user_id).first()

    year = datetime.now(timezone.utc).year
    course_code = _generate_course_code(course.slug)
    sequence = _next_sequence_number(db, year)
    certificate_number = f"GTA-{year}-{course_code}-{sequence:06d}"

    certificate = Certificate(
        user_id=user.id,
        course_id=course.id,
        enrollment_id=enrollment.id,
        payment_id=payment.id,
        certificate_number=certificate_number,
        student_name_snapshot=user.display_name or user.username,
        course_title_snapshot=course.title,
        status=CertificateStatus.VALID,
        issued_at=datetime.now(timezone.utc),
    )
    db.add(certificate)
    db.commit()
    db.refresh(certificate)

    # TODO: generate QR code (qrcode lib) encoding the verification URL
    #   f"{settings.FRONTEND_URL}/verify/{certificate_number}"
    # and a PDF (WeasyPrint, rendering a certificate HTML template with
    # student_name_snapshot, course_title_snapshot, certificate_number, QR
    # image), then upload both to Supabase storage and set:
    #   certificate.qr_code_url = <uploaded QR url>
    #   certificate.pdf_url = <uploaded PDF url>
    # db.commit()

    return certificate


def verify_certificate(db: Session, certificate_number: str) -> Certificate:
    certificate = (
        db.query(Certificate)
        .filter(Certificate.certificate_number == certificate_number)
        .first()
    )
    if not certificate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")
    return certificate


def get_user_certificates(db: Session, user_id: UUID):
    return db.query(Certificate).filter(Certificate.user_id == user_id).all()


def revoke_certificate(db: Session, certificate_id: UUID, reason: str) -> Certificate:
    certificate = db.query(Certificate).filter(Certificate.id == certificate_id).first()
    if not certificate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")

    certificate.status = CertificateStatus.REVOKED
    certificate.revoked_reason = reason
    certificate.revoked_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(certificate)
    return certificate
