"""
app/schemas/payment.py
"""

from typing import Optional, Any, Dict
from uuid import UUID

from pydantic import BaseModel

from app.schemas.base import ORMBase, TimestampedRead, PaymentPurpose, PaymentStatus


class PaymentInitRequest(BaseModel):
    """Kicks off a Paystack transaction, e.g. for a certificate purchase."""
    purpose: PaymentPurpose
    course_id: Optional[UUID] = None  # required if purpose == CERTIFICATE


class PaymentInitResponse(BaseModel):
    """What the frontend needs to redirect the user to Paystack's checkout."""
    authorization_url: str
    access_code: str
    paystack_reference: str


class PaystackWebhookPayload(BaseModel):
    """Raw shape varies by event type — validated loosely, full payload stored for audit."""
    event: str
    data: Dict[str, Any]


class PaymentRead(TimestampedRead):
    user_id: UUID
    purpose: PaymentPurpose
    course_id: Optional[UUID] = None
    amount_kobo: int
    currency: str
    status: PaymentStatus
    paystack_reference: Optional[str] = None
    paystack_channel: Optional[str] = None
    paid_at: Optional[str] = None
