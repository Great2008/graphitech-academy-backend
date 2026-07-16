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
from typing import Optional
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


def issue_certificate(db: Session, user_id: UUID, course_id: UUID, payment: Optional[Payment] = None) -> Certificate:
    """
    Issues a certificate for a completed, eligible enrollment. `payment` is
    optional — when the course has no certificate fee set, this is called
    directly from the "claim" flow with payment=None, so free courses don't
    need Paystack wired up at all to award a real, verifiable certificate.
    """
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
        .first()
    )
    if not enrollment or not enrollment.is_eligible_for_certificate:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Enrollment is not eligible for a certificate — payment cannot be fulfilled",
        )

    if payment is not None:
        existing = db.query(Certificate).filter(Certificate.payment_id == payment.id).first()
        if existing:
            return existing
    else:
        existing = (
            db.query(Certificate)
            .filter(Certificate.enrollment_id == enrollment.id, Certificate.payment_id.is_(None))
            .first()
        )
        if existing:
            return existing

    course = db.query(Course).filter(Course.id == course_id).first()
    user = db.query(User).filter(User.id == user_id).first()

    year = datetime.now(timezone.utc).year
    course_code = _generate_course_code(course.slug)
    sequence = _next_sequence_number(db, year)
    certificate_number = f"GTA-{year}-{course_code}-{sequence:06d}"

    certificate = Certificate(
        user_id=user.id,
        course_id=course.id,
        enrollment_id=enrollment.id,
        payment_id=payment.id if payment else None,
        certificate_number=certificate_number,
        student_name_snapshot=user.display_name or user.username,
        course_title_snapshot=course.title,
        status=CertificateStatus.VALID,
        issued_at=datetime.now(timezone.utc),
    )
    db.add(certificate)
    db.commit()
    db.refresh(certificate)

    _attach_certificate_assets(db, certificate)

    return certificate


def claim_free_certificate(db: Session, user_id: UUID, course_id: UUID) -> Certificate:
    """
    For courses with no certificate_fee_kobo set (or set to 0) — issues the
    certificate directly, no Paystack involvement at all. This is what
    lets certificates work end-to-end before payments are wired up.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if course.certificate_fee_kobo:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="This course's certificate requires payment — use the payment flow instead",
        )
    return issue_certificate(db, user_id, course_id, payment=None)


def _attach_certificate_assets(db: Session, certificate: Certificate) -> None:
    """
    Generates the QR code + PDF and uploads them, then saves the URLs onto
    the certificate. Failures here are logged but never block issuance —
    the certificate record (and its verification number) is the source of
    truth; a missing PDF can be regenerated later without reissuing.
    """
    try:
        from app.services import certificate_pdf_service
        assets = certificate_pdf_service.generate_and_upload_certificate_assets(certificate)
        certificate.pdf_url = assets["pdf_url"]
        certificate.qr_code_url = assets["qr_code_url"]
        db.commit()
    except Exception as exc:  # noqa: BLE001 — asset generation is best-effort, not issuance-blocking
        import logging
        logging.getLogger(__name__).error(
            "Certificate %s issued but asset generation failed: %s",
            certificate.certificate_number, exc,
        )


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


def regenerate_certificate_assets(db: Session, certificate_id: UUID) -> Certificate:
    """Staff utility to retry PDF/QR generation if it failed at issuance time."""
    certificate = db.query(Certificate).filter(Certificate.id == certificate_id).first()
    if not certificate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")
    _attach_certificate_assets(db, certificate)
    db.refresh(certificate)
    return certificate


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
