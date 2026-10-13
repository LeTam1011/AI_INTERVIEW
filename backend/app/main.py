from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.workspace import router as workspace_router
from app.core.config import get_settings
from app.db.database import Base, engine
import app.models  # noqa: F401 - registers SQLAlchemy models before table creation


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Day 1 uses create_all for a zero-friction local setup. Switch to Alembic
    # migrations before deploying or when the schema starts evolving.
    Base.metadata.create_all(bind=engine)
    yield


settings = get_settings()
app = FastAPI(
    title="AI Interview Trainer API",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router, prefix="/api")
app.include_router(workspace_router, prefix="/api")


@app.get("/", tags=["System"])
def root() -> dict[str, str]:
    return {"message": "AI Interview Trainer API is running"}


@app.get("/health", tags=["System"])
def health_check() -> dict[str, str]:
    return {"status": "healthy"}
