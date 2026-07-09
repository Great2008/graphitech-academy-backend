"""
app/services/playground_service.py

Wraps the Judge0 API (self-hosted or RapidAPI-hosted) for the coding
playground. Uses Judge0's synchronous submission mode (?wait=true) so the
route can return a result in one request/response cycle rather than
polling — simpler for v1, at the cost of holding the connection open for
the duration of execution (fine given Judge0's tight time limits).

LANGUAGE_MAP keys match what the frontend sends (Lesson.playground_language
values); values are Judge0's numeric language IDs.
"""

import base64
from typing import Optional

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.playground import PlaygroundRunRequest, PlaygroundRunResponse

# Judge0 CE language IDs — https://ce.judge0.com/ (subset relevant to the academy's tracks)
LANGUAGE_MAP = {
    "python": 71,       # Python 3.8.1
    "javascript": 63,   # Node.js 12.14.0
    "typescript": 74,   # TypeScript 3.7.4
    "java": 62,         # Java OpenJDK 13.0.1
    "c": 50,            # C GCC 9.2.0
    "cpp": 54,          # C++ GCC 9.2.0
    "csharp": 51,       # C# Mono 6.6.0.161
    "go": 60,           # Go 1.13.5
    "ruby": 72,         # Ruby 2.7.0
    "php": 68,          # PHP 7.4.1
    "sql": 82,          # SQLite 3.27.2
}


def _encode(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _decode(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    try:
        return base64.b64decode(text).decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001 — malformed base64 shouldn't crash the response
        return text


def run_code(run_request: PlaygroundRunRequest) -> PlaygroundRunResponse:
    if not settings.JUDGE0_API_URL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Coding playground is not configured (missing JUDGE0_API_URL)",
        )

    language_id = LANGUAGE_MAP.get(run_request.language.lower())
    if language_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language '{run_request.language}'. Supported: {', '.join(LANGUAGE_MAP)}",
        )

    headers = {"Content-Type": "application/json"}
    if settings.JUDGE0_API_KEY:
        # RapidAPI-hosted Judge0 uses these headers; self-hosted instances ignore them.
        headers["X-RapidAPI-Key"] = settings.JUDGE0_API_KEY
        headers["X-RapidAPI-Host"] = "judge0-ce.p.rapidapi.com"

    payload = {
        "language_id": language_id,
        "source_code": _encode(run_request.source_code),
        "stdin": _encode(run_request.stdin),
    }

    try:
        response = httpx.post(
            f"{settings.JUDGE0_API_URL}/submissions",
            params={"base64_encoded": "true", "wait": "true"},
            headers=headers,
            json=payload,
            timeout=20.0,
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not reach the code execution service: {exc}",
        )

    if response.status_code not in (200, 201):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Code execution service returned an unexpected error (status {response.status_code})",
        )

    data = response.json()
    status_info = data.get("status", {})

    return PlaygroundRunResponse(
        status=status_info.get("description", "Unknown"),
        stdout=_decode(data.get("stdout")),
        stderr=_decode(data.get("stderr")),
        compile_output=_decode(data.get("compile_output")),
        time_seconds=float(data["time"]) if data.get("time") else None,
        memory_kb=int(data["memory"]) if data.get("memory") else None,
    )
