"""
app/schemas/analytics.py

AnalyticsEventCreate is intentionally loose (event_type + payload dict) to
match the flexible-schema philosophy in the model. AdminDashboardSummary is
the shaped, aggregated response the admin dashboard actually renders —
computed in the service layer, not stored as-is.
"""

from typing import Optional, Any, Dict
from uuid import UUID

from pydantic import BaseModel

from app.schemas.base import ORMBase, TimestampedRead


class AnalyticsEventCreate(BaseModel):
    event_type: str
    payload: Optional[Dict[str, Any]] = None


class AnalyticsEventRead(TimestampedRead):
    user_id: Optional[UUID] = None
    event_type: str
    payload: Optional[Dict[str, Any]] = None


class AdminDashboardSummary(BaseModel):
    """Aggregated response for the admin growth dashboard (Phase 4)."""
    total_signups: int
    active_learners_30d: int
    total_course_completions: int
    total_certificates_issued: int
    certificate_conversion_rate_percent: float  # completions -> paid certificates
    revenue_kobo_30d: int
    tutor_requests_30d: int


class GrantReadinessSummary(BaseModel):
    """Impact metrics formatted for grant applications (Phase 4)."""
    total_students_enrolled: int
    active_learners: int
    women_in_tech_percent: Optional[float] = None
    completion_rate_percent: float
    states_reached: int
    scholarships_awarded: int
    job_placements_reported: int
    freelancing_success_stories: int
