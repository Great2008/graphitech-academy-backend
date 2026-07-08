"""
app/services/ai_service.py

Uses Groq to draft a full course outline (title, description, lessons,
optional quizzes) from a topic. Output is strict JSON, validated before
anything touches the database — a malformed AI response should fail loud,
not silently corrupt a course.

Nothing here publishes a course. draft_course_with_ai() returns structured
data; course_service.create_course_from_ai_draft() (called by the route)
is what persists it as a DRAFT for an instructor to review and edit.
"""

import json
from typing import Optional

from fastapi import HTTPException, status
from groq import Groq

from app.core.config import settings
from app.schemas.learning import CourseAIDraftRequest

GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are a curriculum designer for GraphiTech Academy, a coding education \
platform. Given a topic, produce a structured course outline as STRICT JSON only — no \
markdown fences, no commentary, no preamble.

Output schema:
{
  "title": string,
  "description": string (2-3 sentences),
  "lessons": [
    {
      "title": string,
      "content_markdown": string (a full lesson written in Markdown — headers, \
explanations, code blocks where relevant; at least 300 words),
      "estimated_minutes": integer,
      "has_quiz": boolean,
      "quiz": {
        "title": string,
        "pass_mark_percent": integer,
        "questions": [
          {"question": string, "options": [string, string, string, string], "correct_index": integer}
        ]
      } | null
    }
  ]
}

Rules:
- Lessons must build progressively from fundamentals to more advanced material.
- Every lesson's content_markdown must be genuinely educational, not a placeholder.
- Only include "quiz" when has_quiz is true; each quiz should have 3-5 questions.
- correct_index is 0-indexed into options.
- Match the requested audience level in tone and pacing.
- Return ONLY the JSON object, nothing else.
"""


def draft_course_with_ai(draft_request: CourseAIDraftRequest) -> dict:
    if not settings.GROQ_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI course drafting is not configured (missing GROQ_API_KEY)",
        )

    client = Groq(api_key=settings.GROQ_API_KEY)

    user_prompt = (
        f"Topic: {draft_request.topic}\n"
        f"Audience level: {draft_request.audience_level}\n"
        f"Target number of lessons: {draft_request.target_lesson_count}\n"
        f"Include quizzes: {draft_request.include_quizzes}\n"
        f"Include a capstone project recommendation in the description: {draft_request.include_capstone}\n"
    )
    if draft_request.additional_instructions:
        user_prompt += f"Additional instructions: {draft_request.additional_instructions}\n"

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            response_format={"type": "json_object"},
        )
    except Exception as exc:  # noqa: BLE001 — surface as a clean 502 rather than a raw SDK error
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI drafting request failed: {exc}",
        )

    raw_content = response.choices[0].message.content

    try:
        draft = json.loads(raw_content)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI returned malformed JSON — try again or adjust the topic",
        )

    _validate_draft_shape(draft)
    return draft


def _validate_draft_shape(draft: dict) -> None:
    required_top_level = {"title", "description", "lessons"}
    if not required_top_level.issubset(draft.keys()):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI draft is missing required fields",
        )
    if not isinstance(draft["lessons"], list) or not draft["lessons"]:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI draft contains no lessons",
        )
    for lesson in draft["lessons"]:
        if not {"title", "content_markdown"}.issubset(lesson.keys()):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI draft lesson is missing required fields",
            )
