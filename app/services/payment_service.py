"""
app/services/payment_service.py

Paystack integration. init_certificate_payment() starts a transaction;
handle_webhook() verifies the signature, marks the Payment paid, and
triggers certificate issuance. Paystack already routes card, bank
transfer, OPay, and Palmpay through one integration — no separate
gateway code needed per channel.
"""

import hashlib
import hmac
import uuid

import httpx
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.models.payment import Payment, PaymentPurpose, PaymentStatus
from app.models.learning import Course
from app.models.enrollment import Enrollment
from app.models.user import User

PAYSTACK_BASE_URL = "https://api.paystack.co"


def init_certificate_payment(db: Session, user: User, course_id: uuid.UUID) -> dict:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if not course.certificate_fee_kobo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This course's certificate has no fee configured")

    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user.id, Enrollment.course_id == course_id)
        .first()
    )
    if not enrollment or not enrollment.is_eligible_for_certificate:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not yet eligible for this certificate. Complete all lessons and the capstone first.",
        )

    reference = f"GTA-{uuid.uuid4().hex[:16]}"

    payment = Payment(
        user_id=user.id,
        purpose=PaymentPurpose.CERTIFICATE,
        course_id=course_id,
        amount_kobo=course.certificate_fee_kobo,
        currency="NGN",
        status=PaymentStatus.PENDING,
        paystack_reference=reference,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    response = httpx.post(
        f"{PAYSTACK_BASE_URL}/transaction/initialize",
        headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"},
        json={
            "email": user.email,
            "amount": course.certificate_fee_kobo,
            "reference": reference,
            "callback_url": f"{settings.FRONTEND_URL}/certificates/payment-callback",
            "metadata": {"payment_id": str(payment.id), "course_id": str(course_id), "user_id": str(user.id)},
        },
        timeout=15.0,
    )

    if response.status_code != 200 or not response.json().get("status"):
        payment.status = PaymentStatus.FAILED
        db.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not initialize payment with Paystack")

    data = response.json()["data"]
    return {
        "authorization_url": data["authorization_url"],
        "access_code": data["access_code"],
        "paystack_reference": reference,
    }


def init_tutor_subscription_payment(db: Session, user: User) -> dict:
    reference = f"GTA-{uuid.uuid4().hex[:16]}"

    payment = Payment(
        user_id=user.id,
        purpose=PaymentPurpose.TUTOR_SUBSCRIPTION,
        course_id=None,
        amount_kobo=settings.TUTOR_SUBSCRIPTION_PRICE_KOBO,
        currency="NGN",
        status=PaymentStatus.PENDING,
        paystack_reference=reference,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    response = httpx.post(
        f"{PAYSTACK_BASE_URL}/transaction/initialize",
        headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"},
        json={
            "email": user.email,
            "amount": settings.TUTOR_SUBSCRIPTION_PRICE_KOBO,
            "reference": reference,
            "callback_url": f"{settings.FRONTEND_URL}/tutor/payment-callback",
            "metadata": {"payment_id": str(payment.id), "user_id": str(user.id), "purpose": "tutor_subscription"},
        },
        timeout=15.0,
    )

    if response.status_code != 200 or not response.json().get("status"):
        payment.status = PaymentStatus.FAILED
        db.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not initialize payment with Paystack")

    data = response.json()["data"]
    return {
        "authorization_url": data["authorization_url"],
        "access_code": data["access_code"],
        "paystack_reference": reference,
    }


def verify_paystack_signature(raw_body: bytes, signature_header: str) -> bool:
    computed = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode("utf-8"),
        raw_body,
        hashlib.sha512,
    ).hexdigest()
    return hmac.compare_digest(computed, signature_header or "")


def handle_successful_payment(db: Session, reference: str, channel: str, raw_payload: dict) -> Payment:
    payment = db.query(Payment).filter(Payment.paystack_reference == reference).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found for reference")

    if payment.status == PaymentStatus.PAID:
        return payment  # already processed — webhook can fire more than once

    from datetime import datetime, timezone

    payment.status = PaymentStatus.PAID
    payment.paystack_channel = channel
    payment.raw_webhook_payload = raw_payload
    payment.paid_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(payment)

    if payment.purpose == PaymentPurpose.CERTIFICATE:
        from app.services import certificate_service
        certificate_service.issue_certificate(db, payment)
    elif payment.purpose == PaymentPurpose.TUTOR_SUBSCRIPTION:
        _extend_tutor_premium(db, payment)

    return payment


def _extend_tutor_premium(db: Session, payment: Payment) -> None:
    """
    Extends from the user's current tutor_premium_until if still active
    (renewal stacks), or from now if expired/never subscribed. Fixed at
    30 days per payment for v1 — make this a plan-based duration later
    if multiple subscription tiers/lengths are introduced.
    """
    from datetime import timedelta

    user = db.query(User).filter(User.id == payment.user_id).first()
    if not user:
        return

    now = datetime.now(timezone.utc)
    base = user.tutor_premium_until if (user.tutor_premium_until and user.tutor_premium_until > now) else now
    user.tutor_premium_until = base + timedelta(days=30)
    db.commit()
