# GraphiTech Academy — Backend

FastAPI backend for GraphiTech Academy.

## Stack
- FastAPI + SQLAlchemy 2.0 + Alembic
- PostgreSQL (via Supabase)
- Groq / Anthropic for AI tutor + course drafting
- Paystack for payments (card, bank transfer, OPay, Palmpay channels)
- Judge0 for the coding playground
- WeasyPrint + qrcode for certificate generation

## Local setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # fill in real values

alembic upgrade head    # run migrations
uvicorn app.main:app --reload
```

API docs available at `http://localhost:8000/docs` once running.

## Project structure

```
app/
  core/       # settings, database session
  models/     # SQLAlchemy models (one file per domain module)
  schemas/    # Pydantic request/response schemas
  routers/    # API routes (added incrementally)
  services/   # business logic (added incrementally)
alembic/      # migrations
```

## Creating a migration

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

## Deployment
Deployed to Render. Set all `.env.example` variables as environment variables
in the Render dashboard — do not commit `.env`.
