"""
app/dependencies.py

Shared FastAPI dependencies: get_current_user (from JWT bearer token) and
require_role (role-based access control for Instructor/Reviewer/Moderator/
Admin/Super Admin-gated routes).
"""

from typing import Iterable
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.models.base import UserRole

# HTTPBearer (not OAuth2PasswordBearer) so Swagger's "Authorize" button shows
# a simple paste-your-token field. OAuth2PasswordBearer would show a
# username/password form that POSTs form-encoded data to tokenUrl — but our
# /api/auth/login endpoint takes JSON with "email"/"password", not OAuth2's
# form-encoded "username"/"password", so that flow doesn't actually work.
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not credentials:
        raise credentials_exception

    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == UUID(user_id)).first()
    if user is None or not user.is_active:
        raise credentials_exception

    return user


def require_role(*allowed_roles: Iterable[UserRole]):
    """
    Usage: Depends(require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
    """
    def _check_role(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return _check_role
