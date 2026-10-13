from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.interview_entities import CareerLevel, InterviewStatus, QuestionType


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ResumeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    original_filename: str | None = Field(default=None, max_length=255)
    raw_text: str | None = None


class ResumeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    original_filename: str | None = Field(default=None, max_length=255)
    raw_text: str | None = None


class ResumeResponse(ORMModel):
    id: int
    user_id: int
    title: str
    original_filename: str | None
    raw_text: str | None
    candidate_profile: dict[str, Any] | None
    cv_score: float | None
    score_feedback: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class JobDescriptionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    company_name: str | None = Field(default=None, max_length=160)
    description: str = Field(min_length=10)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    career_level: CareerLevel = CareerLevel.JUNIOR


class JobDescriptionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    company_name: str | None = Field(default=None, max_length=160)
    description: str | None = Field(default=None, min_length=10)
    required_skills: list[str] | None = None
    preferred_skills: list[str] | None = None
    responsibilities: list[str] | None = None
    career_level: CareerLevel | None = None


class JobDescriptionResponse(ORMModel):
    id: int
    user_id: int
    title: str
    company_name: str | None
    description: str
    required_skills: list[str] | None
    preferred_skills: list[str] | None
    responsibilities: list[str] | None
    career_level: CareerLevel
    created_at: datetime
    updated_at: datetime


class InterviewCreate(BaseModel):
    resume_id: int
    job_description_id: int
    title: str = Field(min_length=1, max_length=180)
    career_level: CareerLevel | None = None
    language: str = Field(default="Vietnamese", min_length=2, max_length=40)


class InterviewStatusUpdate(BaseModel):
    status: InterviewStatus


class InterviewResponse(ORMModel):
    id: int
    user_id: int
    resume_id: int
    job_description_id: int
    title: str
    career_level: CareerLevel
    language: str
    status: InterviewStatus
    context_snapshot: dict[str, Any] | None
    overall_score: float | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class QuestionCreate(BaseModel):
    position: int = Field(ge=1)
    question_text: str = Field(min_length=3)
    question_type: QuestionType = QuestionType.TECHNICAL
    topic: str | None = Field(default=None, max_length=120)
    expected_points: list[str] = Field(default_factory=list)
    source_context: dict[str, Any] | None = None


class QuestionResponse(ORMModel):
    id: int
    interview_id: int
    position: int
    question_text: str
    question_type: QuestionType
    topic: str | None
    expected_points: list[str] | None
    source_context: dict[str, Any] | None
    created_at: datetime


class AnswerCreate(BaseModel):
    answer_text: str = Field(min_length=1)
    duration_seconds: int | None = Field(default=None, ge=0, le=7200)


class AnswerResponse(ORMModel):
    id: int
    question_id: int
    answer_text: str
    duration_seconds: int | None
    created_at: datetime


class EvaluationCreate(BaseModel):
    answer_id: int | None = None
    technical_accuracy: float | None = Field(default=None, ge=0, le=10)
    relevance: float | None = Field(default=None, ge=0, le=10)
    completeness: float | None = Field(default=None, ge=0, le=10)
    communication: float | None = Field(default=None, ge=0, le=10)
    total_score: float = Field(ge=0, le=100)
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    feedback: str | None = None
    evaluator: str = Field(default="manual", max_length=40)

    @model_validator(mode="after")
    def validate_subscores(self):
        scores = [self.technical_accuracy, self.relevance, self.completeness, self.communication]
        provided = [score for score in scores if score is not None]
        if provided and any(score > 10 for score in provided):
            raise ValueError("Subscores must be between 0 and 10")
        return self


class EvaluationResponse(ORMModel):
    id: int
    interview_id: int
    answer_id: int | None
    technical_accuracy: float | None
    relevance: float | None
    completeness: float | None
    communication: float | None
    total_score: float
    strengths: list[str] | None
    improvements: list[str] | None
    feedback: str | None
    evaluator: str
    created_at: datetime


class CVScoreRequest(BaseModel):
    job_description_id: int = Field(gt=0)
    career_level: CareerLevel | None = None
