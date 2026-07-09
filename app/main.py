"""
app/main.py

FastAPI entrypoint. Routers are added as they're built (Phase 1 onward) —
for now this just boots the app with CORS configured for the Vite frontend.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(
    title="GraphiTech Academy API",
    version="0.1.0",
    description="Backend for GraphiTech Academy — Design. Print. Brand. Deploy. Learn.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}


# --- Routers (added incrementally as each flow is built) ---
from app.routers import auth, courses, capstones, payments, certificates, playground, tutor  # noqa: E402

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(courses.router, prefix="/api", tags=["courses"])
app.include_router(capstones.router, prefix="/api", tags=["capstones"])
app.include_router(payments.router, prefix="/api", tags=["payments"])
app.include_router(certificates.router, prefix="/api", tags=["certificates"])
app.include_router(playground.router, prefix="/api", tags=["playground"])
app.include_router(tutor.router, prefix="/api", tags=["tutor"])
