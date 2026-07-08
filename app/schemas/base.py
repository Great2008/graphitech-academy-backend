"""
app/schemas/base.py

Shared Pydantic config. Enums are imported from app.models rather than
redeclared here, so the API layer and the DB layer can never drift apart.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# Re-exported so other schema files can `from app.schemas.base import UserRole` etc.
from app.models.base import (  # noqa: F401
    UserRole,
    CourseStatus,
    EnrollmentStatus,
    QuizAttemptStatus,
    CapstoneStatus,
    CertificateStatus,
)
from app.models.payment import PaymentPurpose, PaymentStatus  # noqa: F401


class ORMBase(BaseModel):
    """Base for schemas that read directly from SQLAlchemy model instances."""
    model_config = ConfigDict(from_attributes=True)


class TimestampedRead(ORMBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
