"""
app/services/playground_service.py

Wraps the Piston API (https://github.com/engineer-man/piston) for the
coding playground — a free, public, no-signup code execution service.

Piston's supported languages/versions change over time, so rather than
hardcoding a list that could silently go stale, we query its /runtimes
endpoint and cache the result in memory. A requested language that isn't
found gets a clear 400 error listing what IS currently supported, instead
of a confusing failure deep in the request.

Note: the public Piston API is rate-limited (documented as ~5 requests/
second per IP). All our students' requests come from this server's IP, so
if usage grows significantly, self-hosting Piston (or switching to Judge0)
is worth revisiting — see PISTON_API_URL in settings.
"""

import time
from typing import Optional

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.playground import PlaygroundRunRequest, PlaygroundRunResponse

# Our own language keys (what the frontend sends, matching
# Lesson.playground_language) mapped to Piston's language names.
# Piston's /runtimes also returns "aliases" we fall back to matching against.
LANGUAGE_ALIASES = {
    "python": "python",
    "javascript": "javascript",
    "typescript": "typescript",
    "java": "java",
    "c": "c",
    "cpp": "c++",
    "csharp": "csharp",
    "go": "go",
    "ruby": "ruby",
    "php": "php",
}

_runtimes_cache: Optional[list] = None
_runtimes_cache_time: float = 0
_RUNTIMES_CACHE_TTL_SECONDS = 3600  # refresh hourly, in case Piston updates versions


def _get_runtimes() -> list:
    global _runtimes_cache, _runtimes_cache_time

    if _runtimes_cache is not None and (time.time() - _runtimes_cache_time) < _RUNTIMES_CACHE_TTL_SECONDS:
        return _runtimes_cache

    try:
        response = httpx.get(f"{settings.PISTON_API_URL}/runtimes", timeout=10.0)
        response.raise_for_status()
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not reach the code execution service: {exc}",
        )

    _runtimes_cache = response.json()
    _runtimes_cache_time = time.time()
    return _runtimes_cache


def _resolve_language(requested: str) -> tuple[str, str]:
    """Returns (piston_language, latest_version) for a requested language key."""
    piston_name = LANGUAGE_ALIASES.get(requested.lower(), requested.lower())
    runtimes = _get_runtimes()

    matches = [
        rt for rt in runtimes
        if rt.get("language") == piston_name or piston_name in rt.get("aliases", [])
    ]

    if not matches:
        supported = sorted({rt["language"] for rt in runtimes})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language '{requested}'. Supported: {', '.join(supported)}",
        )

    # Piston can list multiple versions per language — take the latest.
    latest = sorted(matches, key=lambda rt: rt.get("version", ""))[-1]
    return latest["language"], latest["version"]


def run_code(run_request: PlaygroundRunRequest) -> PlaygroundRunResponse:
    language, version = _resolve_language(run_request.language)

    payload = {
        "language": language,
        "version": version,
        "files": [{"content": run_request.source_code}],
        "stdin": run_request.stdin or "",
    }

    try:
        response = httpx.post(f"{settings.PISTON_API_URL}/execute", json=payload, timeout=20.0)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not reach the code execution service: {exc}",
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Code execution service returned an unexpected error (status {response.status_code})",
        )

    data = response.json()
    run_result = data.get("run", {})
    compile_result = data.get("compile")

    if compile_result and compile_result.get("code", 0) != 0:
        exec_status = "Compilation Error"
    elif run_result.get("signal"):
        exec_status = f"Terminated ({run_result['signal']})"
    elif run_result.get("code", 0) == 0:
        exec_status = "Accepted"
    else:
        exec_status = "Runtime Error"

    return PlaygroundRunResponse(
        status=exec_status,
        stdout=run_result.get("stdout"),
        stderr=run_result.get("stderr"),
        compile_output=compile_result.get("stderr") if compile_result else None,
        time_seconds=None,  # Piston doesn't report execution time
        memory_kb=None,     # or memory usage, unlike Judge0
    )
