# AI Interview Trainer — Backend Foundation

## Stack
- FastAPI
- SQLAlchemy 2.x
- PostgreSQL
- Pydantic v2

## Setup
1. Create/activate a Python 3.11 virtual environment.
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and set your PostgreSQL credentials and a strong `SECRET_KEY`.
4. Run: `uvicorn app.main:app --reload`
5. Open Swagger UI at `http://127.0.0.1:8000/docs`.

This foundation currently uses `Base.metadata.create_all()` for local development. Before production, introduce Alembic migrations.

## API routes
All routes except `/`, `/health`, and registration/login require `Authorization: Bearer <access_token>`.

- `POST /api/resumes`, `GET /api/resumes`, `GET/PATCH/DELETE /api/resumes/{resume_id}`
- `POST /api/jobs`, `GET /api/jobs`, `GET/PATCH/DELETE /api/jobs/{job_id}`
- `POST /api/interviews`, `GET /api/interviews`, `GET /api/interviews/{interview_id}`
- `PATCH /api/interviews/{interview_id}/status`
- `POST/GET /api/interviews/{interview_id}/questions`
- `POST/GET /api/questions/{question_id}/answers`
- `POST/GET /api/interviews/{interview_id}/evaluations`

## Current scope
The API persists CV text/profile fields, job requirements, interview configuration/context snapshots, questions, answers, and evaluations. CV parsing, actual LLM calls, embedding generation, ChromaDB retrieval/RAG, automated CV scoring, and AI-generated evaluation are intentionally not implemented yet; they are next development phases.
