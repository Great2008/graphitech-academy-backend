"""
app/schemas/certificate.py

CertificateVerifyPublic is the schema returned by the PUBLIC verification
page/endpoint (GET /verify/{certificate_number}) — no auth required, since
the whole point is that employers can check it. Deliberately minimal.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.schemas.base import ORMBase, TimestampedRead, CertificateStatus


class CertificateIssueRequest(BaseModel):
    """Triggered internally once payment is confirmed + enrollment is eligible."""
    enrollment_id: UUID
    payment_id: UUID


class CertificateRevoke(BaseModel):
    """Admin/Super Admin only."""
    reason: str


class CertificateRead(TimestampedRead):
    user_id: UUID
    course_id: UUID
    enrollment_id: UUID
    certificate_number: str
    student_name_snapshot: str
    course_title_snapshot: str
    grade_percent: Optional[int] = None
    status: CertificateStatus
    issued_at: Optional[str] = None
    pdf_url: Optional[str] = None
    qr_code_url: Optional[str] = None


class CertificateVerifyPublic(ORMBase):
    """Public, no-auth verification response."""
    certificate_number: str
    student_name_snapshot: str
    course_title_snapshot: str
    grade_percent: Optional[int] = None
    status: CertificateStatus
    issued_at: Optional[str] = None
