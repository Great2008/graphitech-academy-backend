"""
app/routers/auth.py

POST /api/auth/signup
POST /api/auth/login
GET  /api/auth/me
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenWithUser
from app.schemas.user import UserCreate, UserRead
from app.services import auth_service

router = APIRouter()


@router.post("/signup", response_model=TokenWithUser, status_code=201)
def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    user = auth_service.create_user(db, user_in)
    token = create_access_token(user.id)
    return TokenWithUser(access_token=token, user=UserRead.model_validate(user))


@router.post("/login", response_model=TokenWithUser)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = auth_service.authenticate_user(db, credentials.email, credentials.password)
    token = create_access_token(user.id)
    return TokenWithUser(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
