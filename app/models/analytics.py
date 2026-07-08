"""
app/models/analytics.py

Generic event log for growth tracking (Phase 4). Rather than a rigid table
per metric, events are logged with a type + JSON payload, then aggregated
in reporting queries or exported to PostHog. Keeps the schema flexible as
new metrics get added (e.g. grant-readiness reporting) without migrations.

Example events:
  - "user_signed_up"          {"referral_source": "instagram"}
  - "lesson_completed"        {"lesson_id": "...", "course_id": "..."}
  - "course_completed"        {"course_id": "...", "days_to_complete": 21}
  - "certificate_purchased"   {"certificate_id": "...", "amount_kobo": 500000}
  - "capstone_submitted"      {"course_id": "..."}
  - "scholarship_awarded"     {"amount_kobo": 0, "note": "..."}
"""

from sqlalchemy import Column, String, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, UUIDMixin, TimestampMixin


class AnalyticsEvent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "analytics_events"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # null for anonymous/system events
    event_type = Column(String, nullable=False, index=True)
    payload = Column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<AnalyticsEvent {self.event_type}>"
