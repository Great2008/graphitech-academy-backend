"""
app/models/__init__.py

Import every model here so SQLAlchemy can resolve string-based relationship()
references across files (e.g. User.certificates -> "Certificate") when
Base.metadata.create_all() or Alembic autogenerate runs.
"""

from app.models.base import Base  # noqa: F401

from app.models.user import User  # noqa: F401
from app.models.learning import LearningPath, Course, Lesson  # noqa: F401
from app.models.enrollment import Enrollment, Progress  # noqa: F401
from app.models.assessment import Quiz, QuizAttempt, CapstoneSubmission  # noqa: F401
from app.models.certificate import Certificate  # noqa: F401
from app.models.badge import Badge, UserBadge  # noqa: F401
from app.models.project import Project, ProjectComment  # noqa: F401
from app.models.ai_tutor import TutorUsage  # noqa: F401
from app.models.payment import Payment  # noqa: F401
from app.models.analytics import AnalyticsEvent  # noqa: F401
