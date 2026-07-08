"""
app/models/payment.py

Payment records for certificate purchases (Phase 2/4) and, later, premium
tutor subscriptions. Paystack is the primary gateway — it already routes
card, bank transfer, OPay, and Palmpay channels, so one integration covers
all of them.
"""

import enum

from sqlalchemy import Column, String, Integer, ForeignKey, Enum, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class PaymentPurpose(str, enum.Enum):
    CERTIFICATE = "certificate"
    TUTOR_SUBSCRIPTION = "tutor_subscription"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class Payment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "payments"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    purpose = Column(Enum(PaymentPurpose), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=True)  # for certificate payments

    amount_kobo = Column(Integer, nullable=False)  # NGN minor unit
    currency = Column(String, default="NGN", nullable=False)

    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)

    paystack_reference = Column(String, unique=True, nullable=True, index=True)
    paystack_channel = Column(String, nullable=True)  # e.g. "card", "bank_transfer", "opay", "palmpay"
    raw_webhook_payload = Column(JSON, nullable=True)  # for auditing/debugging

    paid_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<Payment user={self.user_id} purpose={self.purpose} status={self.status}>"
