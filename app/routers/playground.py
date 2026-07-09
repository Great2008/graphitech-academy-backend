"""
app/routers/playground.py

Student (authenticated):
  POST /api/playground/run

Requires auth mainly so misuse/abuse can be traced to a user — code
execution against Judge0 has a real compute cost even at free-tier volumes.
"""

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.playground import PlaygroundRunRequest, PlaygroundRunResponse
from app.services import playground_service

router = APIRouter()


@router.post("/playground/run", response_model=PlaygroundRunResponse)
def run_code(
    run_request: PlaygroundRunRequest,
    current_user: User = Depends(get_current_user),
):
    return playground_service.run_code(run_request)
