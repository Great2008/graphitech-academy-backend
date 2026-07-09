"""
app/routers/payments.py

Student (authenticated):
  POST /api/payments/certificate/{course_id}   (init Paystack transaction)

Public (called by Paystack, verified via signature header):
  POST /api/payments/webhook
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.payment import PaymentInitResponse
from app.services import payment_service

router = APIRouter()


@router.post("/payments/certificate/{course_id}", response_model=PaymentInitResponse)
def init_certificate_payment(
    course_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return payment_service.init_certificate_payment(db, current_user, course_id)


@router.post("/payments/tutor-subscription", response_model=PaymentInitResponse)
def init_tutor_subscription_payment(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return payment_service.init_tutor_subscription_payment(db, current_user)


@router.post("/payments/webhook", status_code=200)
async def paystack_webhook(request: Request, db: Session = Depends(get_db)):
    raw_body = await request.body()
    signature = request.headers.get("x-paystack-signature", "")

    if not payment_service.verify_paystack_signature(raw_body, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

    payload = await request.json()
    event = payload.get("event")

    if event == "charge.success":
        data = payload.get("data", {})
        reference = data.get("reference")
        channel = data.get("channel", "unknown")
        if reference:
            payment_service.handle_successful_payment(db, reference, channel, payload)

    return {"status": "received"}
