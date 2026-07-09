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


# ---------------------------------------------------------------------------
# AI Tutor chat
# ---------------------------------------------------------------------------

TUTOR_SYSTEM_PROMPT = """You are the GraphiTech Academy AI Tutor, helping students learn to code. \
Follow these rules strictly:

1. NEVER simply hand over a complete solution to a quiz question, exercise, or capstone \
requirement. If a student asks you to "write the code for me", "give me the answer", or \
similar, do not comply directly — instead guide them toward the answer: ask what they've \
tried, point out the concept they need, or walk through a similar-but-different example. \
You may give short illustrative code snippets to explain a CONCEPT, but never a \
drop-in solution to their actual assignment.

2. If you are not confident in your answer (unfamiliar library, ambiguous question, \
something that may have changed since your training, or genuinely uncertain), start your \
reply with the exact token "LOW_CONFIDENCE:" followed by your answer. Do not use this \
token unless you are genuinely uncertain.

3. Be encouraging and concise. Match the student's apparent skill level. Use Markdown code \
blocks for any code you do include.

4. Stay focused on coding education, AI productivity, and career development topics \
relevant to the academy. Politely redirect off-topic requests.
"""


def chat_with_tutor(message: str, is_premium: bool) -> dict:
    """
    Returns {"reply": str, "low_confidence_flag": bool, "plagiarism_nudge": Optional[str]}.
    Plagiarism-risk detection is a simple keyword heuristic on the OUTGOING
    student message — kept intentionally lightweight for v1; the system
    prompt is the primary defense, this is just a UI signal.
    """
    if not settings.GROQ_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI tutor is not configured (missing GROQ_API_KEY)",
        )

    client = Groq(api_key=settings.GROQ_API_KEY)

    model = GROQ_MODEL if not is_premium else GROQ_MODEL  # placeholder for a stronger premium model later

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": TUTOR_SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            temperature=0.5,
            max_tokens=800,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI tutor request failed: {exc}",
        )

    raw_reply = response.choices[0].message.content or ""

    low_confidence_flag = raw_reply.startswith("LOW_CONFIDENCE:")
    reply = raw_reply.replace("LOW_CONFIDENCE:", "", 1).strip() if low_confidence_flag else raw_reply

    plagiarism_nudge = None
    if _looks_like_plagiarism_risk(message):
        plagiarism_nudge = "Try explaining your approach first — I can check your reasoning and point you in the right direction."

    return {
        "reply": reply,
        "low_confidence_flag": low_confidence_flag,
        "plagiarism_nudge": plagiarism_nudge,
        "model_used": model,
    }


_PLAGIARISM_RISK_PHRASES = (
    "write the code for me",
    "give me the answer",
    "give me the solution",
    "just do my",
    "solve this for me",
    "do my quiz",
    "do my assignment",
    "do my capstone",
    "complete code for",
)


def _looks_like_plagiarism_risk(message: str) -> bool:
    lowered = message.lower()
    return any(phrase in lowered for phrase in _PLAGIARISM_RISK_PHRASES)
