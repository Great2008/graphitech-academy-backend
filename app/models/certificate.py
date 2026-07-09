"""
app/models/certificate.py

Certificates are issued only after:
  1. Enrollment.is_eligible_for_certificate == True (capstone approved,
     pass marks met), AND
  2. Payment for this certificate is confirmed (Payment model, status=paid)

certificate_number is the human-readable ID shown on the PDF and used in
the public verification URL, e.g.:
  https://graphitechacademy.org/verify/GTA-2026-WD-000123

qr_code_url points to a generated QR image encoding the verification URL.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, UUIDMixin, TimestampMixin, CertificateStatus, pg_enum


class Certificate(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "certificates"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    enrollment_id = Column(UUID(as_uuid=True), ForeignKey("enrollments.id"), nullable=False)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=True)

    # e.g. "GTA-2026-WD-000123" — GTA / year / course-code / sequence
    certificate_number = Column(String, unique=True, nullable=False, index=True)

    student_name_snapshot = Column(String, nullable=False)  # frozen at issue time
    course_title_snapshot = Column(String, nullable=False)
    grade_percent = Column(Integer, nullable=True)  # optional

    status = Column(pg_enum(CertificateStatus, "certificatestatus"), default=CertificateStatus.VALID, nullable=False)
    revoked_reason = Column(String, nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    issued_at = Column(DateTime(timezone=True), nullable=True)
    pdf_url = Column(String, nullable=True)  # generated PDF in storage
    qr_code_url = Column(String, nullable=True)

    user = relationship("User", back_populates="certificates")

    def __repr__(self) -> str:
        return f"<Certificate {self.certificate_number} status={self.status}>"
