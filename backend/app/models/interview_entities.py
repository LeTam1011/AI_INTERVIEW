import enum
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text, Float, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class CareerLevel(str, enum.Enum):
    INTERN = "intern"
    FRESHER = "fresher"
    JUNIOR = "junior"
    MIDDLE = "middle"
    SENIOR = "senior"


class InterviewStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class QuestionType(str, enum.Enum):
    CV_BASED = "cv_based"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    SITUATIONAL = "situational"
    FOLLOW_UP = "follow_up"


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255))
    file_path: Mapped[str | None] = mapped_column(String(500))
    raw_text: Mapped[str | None] = mapped_column(Text)
    candidate_profile: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    cv_score: Mapped[float | None] = mapped_column(Float)
    score_feedback: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    interviews: Mapped[list["Interview"]] = relationship(back_populates="resume")


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    required_skills: Mapped[list[str] | None] = mapped_column(JSON)
    preferred_skills: Mapped[list[str] | None] = mapped_column(JSON)
    responsibilities: Mapped[list[str] | None] = mapped_column(JSON)
    career_level: Mapped[CareerLevel] = mapped_column(Enum(CareerLevel, name="career_level"), default=CareerLevel.JUNIOR, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    interviews: Mapped[list["Interview"]] = relationship(back_populates="job_description")


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id", ondelete="RESTRICT"), nullable=False)
    job_description_id: Mapped[int] = mapped_column(ForeignKey("job_descriptions.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    career_level: Mapped[CareerLevel] = mapped_column(Enum(CareerLevel, name="career_level"), nullable=False)
    language: Mapped[str] = mapped_column(String(40), default="Vietnamese", nullable=False)
    status: Mapped[InterviewStatus] = mapped_column(Enum(InterviewStatus, name="interview_status"), default=InterviewStatus.DRAFT, nullable=False)
    context_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    overall_score: Mapped[float | None] = mapped_column(Float)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    resume: Mapped[Resume] = relationship(back_populates="interviews")
    job_description: Mapped[JobDescription] = relationship(back_populates="interviews")
    questions: Mapped[list["Question"]] = relationship(back_populates="interview", cascade="all, delete-orphan", order_by="Question.position")
    evaluations: Mapped[list["Evaluation"]] = relationship(back_populates="interview", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"), index=True, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(Enum(QuestionType, name="question_type"), default=QuestionType.TECHNICAL, nullable=False)
    topic: Mapped[str | None] = mapped_column(String(120))
    expected_points: Mapped[list[str] | None] = mapped_column(JSON)
    source_context: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    interview: Mapped[Interview] = relationship(back_populates="questions")
    answers: Mapped[list["Answer"]] = relationship(back_populates="question", cascade="all, delete-orphan")


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True, nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    question: Mapped[Question] = relationship(back_populates="answers")
    evaluation: Mapped["Evaluation | None"] = relationship(back_populates="answer", cascade="all, delete-orphan", uselist=False)


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"), index=True, nullable=False)
    answer_id: Mapped[int | None] = mapped_column(ForeignKey("answers.id", ondelete="CASCADE"), unique=True)
    technical_accuracy: Mapped[float | None] = mapped_column(Float)
    relevance: Mapped[float | None] = mapped_column(Float)
    completeness: Mapped[float | None] = mapped_column(Float)
    communication: Mapped[float | None] = mapped_column(Float)
    total_score: Mapped[float] = mapped_column(Float, nullable=False)
    strengths: Mapped[list[str] | None] = mapped_column(JSON)
    improvements: Mapped[list[str] | None] = mapped_column(JSON)
    feedback: Mapped[str | None] = mapped_column(Text)
    evaluator: Mapped[str] = mapped_column(String(40), default="manual", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    interview: Mapped[Interview] = relationship(back_populates="evaluations")
    answer: Mapped[Answer | None] = relationship(back_populates="evaluation")
