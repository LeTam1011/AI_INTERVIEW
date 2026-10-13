from datetime import datetime, timezone

from app.ai.cv_scorer import score_cv

from fastapi import Query
from app.ai.rag_question_generator import generate_rag_questions

from app.ai.follow_up_generator import generate_follow_up

from app.ai.answer_evaluator import evaluate_answer


from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.ai.cv_parser import MAX_UPLOAD_BYTES, parse_cv
from app.models.interview_entities import (
    Answer, CareerLevel, Evaluation, Interview, InterviewStatus, JobDescription,
    Question, QuestionType, Resume,
)
from app.schemas.workspace import (
    CVScoreRequest,AnswerCreate, AnswerResponse, EvaluationCreate, EvaluationResponse,
    InterviewCreate, InterviewResponse, InterviewStatusUpdate,
    JobDescriptionCreate, JobDescriptionResponse, JobDescriptionUpdate,
    QuestionCreate, QuestionResponse, ResumeCreate, ResumeResponse, ResumeUpdate,
)

router = APIRouter(tags=["Interview Workspace"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Resource not found")


# Resumes


@router.post("/resumes/upload", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
async def upload_and_parse_resume(
    db: DbSession,
    user: CurrentUser,
    file: UploadFile = File(...),
):
    """Upload a PDF/DOCX CV, extract text, and persist a first-pass profile."""
    filename = (file.filename or "").replace("\\", "/").split("/")[-1].strip()
    if not filename:
        raise HTTPException(status_code=400, detail="A filename is required")

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the 5 MB upload limit")
    try:
        parsed = parse_cv(filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    title = filename.rsplit(".", 1)[0][:160].strip() or "Uploaded CV"
    resume = Resume(
        user_id=user.id,
        title=title,
        original_filename=filename[:255],
        raw_text=parsed.text,
        candidate_profile=parsed.profile,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume

@router.post("/resumes", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
def create_resume(payload: ResumeCreate, db: DbSession, user: CurrentUser):
    resume = Resume(user_id=user.id, title=payload.title.strip(), original_filename=payload.original_filename, raw_text=payload.raw_text)
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@router.get("/resumes", response_model=list[ResumeResponse])
def list_resumes(db: DbSession, user: CurrentUser):
    return list(db.scalars(select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc())))


@router.get("/resumes/{resume_id}", response_model=ResumeResponse)
def get_resume(resume_id: int, db: DbSession, user: CurrentUser):
    resume = db.scalar(select(Resume).where(Resume.id == resume_id, Resume.user_id == user.id))
    if resume is None:
        raise _not_found()
    return resume


@router.patch("/resumes/{resume_id}", response_model=ResumeResponse)
def update_resume(resume_id: int, payload: ResumeUpdate, db: DbSession, user: CurrentUser):
    resume = db.scalar(select(Resume).where(Resume.id == resume_id, Resume.user_id == user.id))
    if resume is None:
        raise _not_found()
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(resume, key, value.strip() if key == "title" and value else value)
    db.commit()
    db.refresh(resume)
    return resume


@router.delete("/resumes/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(resume_id: int, db: DbSession, user: CurrentUser):
    resume = db.scalar(select(Resume).where(Resume.id == resume_id, Resume.user_id == user.id))
    if resume is None:
        raise _not_found()
    if db.scalar(select(Interview.id).where(Interview.resume_id == resume_id).limit(1)) is not None:
        raise HTTPException(status_code=409, detail="Resume is linked to an interview and cannot be deleted")
    db.delete(resume)
    db.commit()



@router.post("/resumes/{resume_id}/score")
def calculate_resume_score(
    resume_id: int,
    payload: CVScoreRequest,
    db: DbSession,
    user: CurrentUser,
):
    """Score a user's CV against one of their own job descriptions."""

    resume = db.scalar(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == user.id,
        )
    )
    if resume is None:
        raise _not_found()

    job = db.scalar(
        select(JobDescription).where(
            JobDescription.id == payload.job_description_id,
            JobDescription.user_id == user.id,
        )
    )
    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job description not found",
        )

    level = payload.career_level or job.career_level

    try:
        result = score_cv(
            resume_text=resume.raw_text or "",
            candidate_profile=resume.candidate_profile,
            job_title=job.title,
            job_description=job.description,
            required_skills=job.required_skills or [],
            preferred_skills=job.preferred_skills or [],
            responsibilities=job.responsibilities or [],
            career_level=level.value,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    # Persist the overall score and detailed feedback in existing columns.
    resume.cv_score = result["overall_score"]
    resume.score_feedback = {
        **result,
        "job_description_id": job.id,
        "job_title": job.title,
        "career_level": level.value,
    }

    db.commit()
    db.refresh(resume)

    return {
        "resume_id": resume.id,
        "resume_title": resume.title,
        "job_description_id": job.id,
        "job_title": job.title,
        **result,
    }


@router.get("/resumes/{resume_id}/score")
def get_resume_score(
    resume_id: int,
    db: DbSession,
    user: CurrentUser,
):
    """Return the most recently saved CV score for this resume."""

    resume = db.scalar(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == user.id,
        )
    )
    if resume is None:
        raise _not_found()

    if resume.cv_score is None or not resume.score_feedback:
        raise HTTPException(
            status_code=404,
            detail="This CV has not been scored yet",
        )

    return {
        "resume_id": resume.id,
        "resume_title": resume.title,
        "overall_score": resume.cv_score,
        **resume.score_feedback,
    }


# Job descriptions
@router.post("/jobs", response_model=JobDescriptionResponse, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobDescriptionCreate, db: DbSession, user: CurrentUser):
    job = JobDescription(user_id=user.id, **payload.model_dump())
    job.title = job.title.strip()
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/jobs", response_model=list[JobDescriptionResponse])
def list_jobs(db: DbSession, user: CurrentUser):
    return list(db.scalars(select(JobDescription).where(JobDescription.user_id == user.id).order_by(JobDescription.created_at.desc())))


@router.get("/jobs/{job_id}", response_model=JobDescriptionResponse)
def get_job(job_id: int, db: DbSession, user: CurrentUser):
    job = db.scalar(select(JobDescription).where(JobDescription.id == job_id, JobDescription.user_id == user.id))
    if job is None:
        raise _not_found()
    return job


@router.patch("/jobs/{job_id}", response_model=JobDescriptionResponse)
def update_job(job_id: int, payload: JobDescriptionUpdate, db: DbSession, user: CurrentUser):
    job = db.scalar(select(JobDescription).where(JobDescription.id == job_id, JobDescription.user_id == user.id))
    if job is None:
        raise _not_found()
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(job, key, value.strip() if key == "title" and value else value)
    db.commit()
    db.refresh(job)
    return job


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: int, db: DbSession, user: CurrentUser):
    job = db.scalar(select(JobDescription).where(JobDescription.id == job_id, JobDescription.user_id == user.id))
    if job is None:
        raise _not_found()
    if db.scalar(select(Interview.id).where(Interview.job_description_id == job_id).limit(1)) is not None:
        raise HTTPException(status_code=409, detail="Job description is linked to an interview and cannot be deleted")
    db.delete(job)
    db.commit()


# Interviews
@router.post("/interviews", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
def create_interview(payload: InterviewCreate, db: DbSession, user: CurrentUser):
    resume = db.scalar(select(Resume).where(Resume.id == payload.resume_id, Resume.user_id == user.id))
    job = db.scalar(select(JobDescription).where(JobDescription.id == payload.job_description_id, JobDescription.user_id == user.id))
    if resume is None or job is None:
        raise HTTPException(status_code=404, detail="Resume or job description not found")
    
    level = payload.career_level or job.career_level

    # Reuse the saved score only when it belongs to this JD and level.
    saved_feedback = resume.score_feedback or {}
    cv_score_result = None

    if (
        resume.cv_score is not None
        and saved_feedback.get("job_description_id") == job.id
        and saved_feedback.get("career_level") == level.value
    ):
        cv_score_result = saved_feedback
    else:
        try:
            cv_score_result = score_cv(
                resume_text=resume.raw_text or "",
                candidate_profile=resume.candidate_profile,
                job_title=job.title,
                job_description=job.description,
                required_skills=job.required_skills or [],
                preferred_skills=job.preferred_skills or [],
                responsibilities=job.responsibilities or [],
                career_level=level.value,
            )

            # Persist the most recent CV score using existing columns.
            resume.cv_score = cv_score_result["overall_score"]
            resume.score_feedback = {
                **cv_score_result,
                "job_description_id": job.id,
                "job_title": job.title,
                "career_level": level.value,
            }
        except ValueError:
            # Do not block interview creation when the CV has no usable text.
            cv_score_result = None

    cv_score_context = None

    if cv_score_result:
        cv_score_context = {
            "overall_score": cv_score_result.get("overall_score"),
            "career_level": level.value,
            "breakdown": cv_score_result.get("breakdown", {}),
            "matched_required_skills": cv_score_result.get(
                "matched_required_skills", []
            ),
            "missing_required_skills": cv_score_result.get(
                "missing_required_skills", []
            ),
            "matched_preferred_skills": cv_score_result.get(
                "matched_preferred_skills", []
            ),
            "strengths": cv_score_result.get("strengths", []),
            "improvements": cv_score_result.get("improvements", []),
            "job_description_id": job.id,
        }

    context_snapshot = {
        "candidate_profile": resume.candidate_profile or {},
        "resume_text": resume.raw_text or "",
        "cv_score": cv_score_context,
        "job": {
            "title": job.title,
            "company_name": job.company_name,
            "description": job.description,
            "required_skills": job.required_skills or [],
            "preferred_skills": job.preferred_skills or [],
            "responsibilities": job.responsibilities or [],
        },
        "career_level": level.value,
        "language": payload.language,
        "context_version": 2,
    }

    interview = Interview(
        user_id=user.id,
        resume_id=resume.id,
        job_description_id=job.id,
        title=payload.title.strip(),
        career_level=level,
        language=payload.language,
        context_snapshot=context_snapshot,
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return interview


@router.get("/interviews", response_model=list[InterviewResponse])
def list_interviews(db: DbSession, user: CurrentUser):
    return list(db.scalars(select(Interview).where(Interview.user_id == user.id).order_by(Interview.created_at.desc())))


@router.get("/interviews/{interview_id}", response_model=InterviewResponse)
def get_interview(interview_id: int, db: DbSession, user: CurrentUser):
    interview = db.scalar(select(Interview).where(Interview.id == interview_id, Interview.user_id == user.id))
    if interview is None:
        raise _not_found()
    return interview


@router.patch("/interviews/{interview_id}/status", response_model=InterviewResponse)
def update_interview_status(interview_id: int, payload: InterviewStatusUpdate, db: DbSession, user: CurrentUser):
    interview = db.scalar(select(Interview).where(Interview.id == interview_id, Interview.user_id == user.id))
    if interview is None:
        raise _not_found()
    now = datetime.now(timezone.utc)
    if payload.status == InterviewStatus.IN_PROGRESS and interview.started_at is None:
        interview.started_at = now
    if payload.status == InterviewStatus.COMPLETED:
        interview.completed_at = now
    interview.status = payload.status
    db.commit()
    db.refresh(interview)
    return interview


# Questions and answers
@router.post("/interviews/{interview_id}/questions", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
def create_question(interview_id: int, payload: QuestionCreate, db: DbSession, user: CurrentUser):
    interview = db.scalar(select(Interview).where(Interview.id == interview_id, Interview.user_id == user.id))
    if interview is None:
        raise _not_found()
    question = Question(interview_id=interview.id, **payload.model_dump())
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@router.post(
    "/interviews/{interview_id}/generate-questions",
    response_model=list[QuestionResponse],
    status_code=status.HTTP_201_CREATED,
)
def generate_interview_questions(
    interview_id: int,
    db: DbSession,
    user: CurrentUser,
    count: int = Query(default=10, ge=1, le=20),
):
    """Generate and persist interview questions from the saved CV/JD context."""

    interview = db.scalar(
        select(Interview).where(
            Interview.id == interview_id,
            Interview.user_id == user.id,
        )
    )

    if interview is None:
        raise _not_found()

    # Avoid creating duplicate questions when called repeatedly.
    existing_question = db.scalar(
        select(Question.id)
        .where(Question.interview_id == interview_id)
        .limit(1)
    )

    if existing_question is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Questions already exist for this interview. "
                "Create a new interview to generate a new set."
            ),
        )

    context = interview.context_snapshot or {}

    generated = generate_rag_questions(
    context_snapshot=context,
    count=count,
)

    if not generated:
        raise HTTPException(
            status_code=422,
            detail="Could not generate questions from the interview context",
        )

    try:
        for item in generated:
            # Validate the generated fields against the project's schema.
            payload = QuestionCreate(**item)

            question = Question(
                interview_id=interview.id,
                **payload.model_dump(),
            )
            db.add(question)

        db.commit()

    except Exception:
        db.rollback()
        raise

    return list(
        db.scalars(
            select(Question)
            .where(Question.interview_id == interview_id)
            .order_by(Question.position)
        )
    )



@router.post(
    "/questions/{question_id}/follow-up",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
)

def create_follow_up_question(
    question_id: int,
    db: DbSession,
    user: CurrentUser,
):
    """Generate and save a follow-up question using the latest answer and evaluation."""

    question = db.scalar(
        select(Question)
        .join(Interview, Question.interview_id == Interview.id)
        .where(
            Question.id == question_id,
            Interview.user_id == user.id,
        )
    )

    if question is None:
        raise _not_found()

    answer = db.scalar(
        select(Answer)
        .where(Answer.question_id == question.id)
        .order_by(Answer.created_at.desc(), Answer.id.desc())
        .limit(1)
    )

    if answer is None:
        raise HTTPException(
            status_code=400,
            detail="The original question has no answer yet",
        )

    interview = db.get(Interview, question.interview_id)
    context = (interview.context_snapshot or {}) if interview else {}

    existing_questions = list(
        db.scalars(
            select(Question).where(
                Question.interview_id == question.interview_id
            )
        )
    )

    # Prevent duplicate follow-up questions.
    for existing in existing_questions:
        source = existing.source_context or {}

        if (
            existing.question_type == QuestionType.FOLLOW_UP
            and source.get("parent_question_id") == question.id
        ):
            raise HTTPException(
                status_code=409,
                detail="A follow-up question already exists for this question",
            )

    # Retrieve the evaluation associated with the latest answer.
    evaluation = db.scalar(
        select(Evaluation)
        .where(Evaluation.answer_id == answer.id)
        .order_by(Evaluation.created_at.desc(), Evaluation.id.desc())
        .limit(1)
    )

    expected_points = list(question.expected_points or [])

    # Prefer missing criteria identified by the evaluator.

    if evaluation:
    # Chỉ dùng tiêu chí gốc, không dùng nhận xét chung
    # làm expected_points.
        expected_points = list(question.expected_points or [])

        if evaluation.total_score < 60:
            generated_hint = (
            "Câu trả lời trước có điểm thấp. "
            "Hãy tập trung làm rõ kiến thức còn thiếu, "
            "yêu cầu giải thích và ví dụ cụ thể."
            )
        elif evaluation.total_score >= 80:
            generated_hint = (
            "Câu trả lời trước có điểm tốt. "
            "Hãy hỏi sâu hơn bằng một tình huống thực tế "
            "hoặc yêu cầu giải thích lý do lựa chọn."
            )
        else:
            generated_hint = (
            "Hãy làm rõ câu trả lời trước "
            "và yêu cầu ví dụ cụ thể."
        )
    else:
    # Chưa có đánh giá cho câu trả lời.
        expected_points = list(question.expected_points or [])
        generated_hint = (
        "Chưa có đánh giá trước đó. "
        "Hãy yêu cầu ứng viên giải thích rõ hơn "
        "và đưa ví dụ."
    )


    
    generated = generate_follow_up(
        question_text=question.question_text,
        answer_text=answer.answer_text,
        expected_points=expected_points,
        topic=question.topic,
        language=context.get("language", "vi"),
        evaluation_score=(
            evaluation.total_score if evaluation else None
        ),
        evaluation_hint=generated_hint,
    )

    # generated["source_context"]["evaluation_hint"] = generated_hint

    # Preserve traceability to the original question, answer, and evaluation.
    generated["source_context"]["parent_question_id"] = question.id
    generated["source_context"]["answer_id"] = answer.id

    if evaluation:
        generated["source_context"]["evaluation_id"] = evaluation.id
        generated["source_context"]["evaluation_score"] = (
            evaluation.total_score
        )

    last_position = max(
        (item.position for item in existing_questions),
        default=0,
    )

    payload = QuestionCreate(
        position=last_position + 1,
        **generated,
    )

    follow_up = Question(
        interview_id=question.interview_id,
        **payload.model_dump(),
    )

    db.add(follow_up)
    db.commit()
    db.refresh(follow_up)

    return follow_up


@router.get("/interviews/{interview_id}/questions", response_model=list[QuestionResponse])
def list_questions(interview_id: int, db: DbSession, user: CurrentUser):
    interview = db.scalar(select(Interview).where(Interview.id == interview_id, Interview.user_id == user.id))
    if interview is None:
        raise _not_found()
    return list(db.scalars(select(Question).where(Question.interview_id == interview_id).order_by(Question.position)))


@router.post("/questions/{question_id}/answers", response_model=AnswerResponse, status_code=status.HTTP_201_CREATED)
def create_answer(question_id: int, payload: AnswerCreate, db: DbSession, user: CurrentUser):
    question = db.scalar(select(Question).join(Interview).where(Question.id == question_id, Interview.user_id == user.id))
    if question is None:
        raise _not_found()
    answer = Answer(question_id=question.id, **payload.model_dump())
    db.add(answer)
    db.commit()
    db.refresh(answer)
    return answer


@router.get("/questions/{question_id}/answers", response_model=list[AnswerResponse])
def list_answers(question_id: int, db: DbSession, user: CurrentUser):
    question = db.scalar(select(Question).join(Interview).where(Question.id == question_id, Interview.user_id == user.id))
    if question is None:
        raise _not_found()
    return list(db.scalars(select(Answer).where(Answer.question_id == question_id).order_by(Answer.created_at)))


# Evaluations (currently persisted scores/feedback; AI evaluator comes in a later phase)
@router.post("/interviews/{interview_id}/evaluations", response_model=EvaluationResponse, status_code=status.HTTP_201_CREATED)
def create_evaluation(interview_id: int, payload: EvaluationCreate, db: DbSession, user: CurrentUser):
    interview = db.scalar(select(Interview).where(Interview.id == interview_id, Interview.user_id == user.id))
    if interview is None:
        raise _not_found()
    if payload.answer_id is not None:
        answer = db.scalar(
            select(Answer).join(Question).where(
                Answer.id == payload.answer_id,
                Question.interview_id == interview_id,
            )
        )
        if answer is None:
            raise HTTPException(status_code=400, detail="Answer does not belong to this interview")
        existing = db.scalar(select(Evaluation).where(Evaluation.answer_id == payload.answer_id))
        if existing is not None:
            raise HTTPException(status_code=409, detail="This answer already has an evaluation")
    evaluation = Evaluation(interview_id=interview_id, **payload.model_dump())
    db.add(evaluation)
    db.flush()
    evaluations = list(db.scalars(select(Evaluation).where(Evaluation.interview_id == interview_id)))
    interview.overall_score = round(sum(item.total_score for item in evaluations) / len(evaluations), 2)
    db.commit()
    db.refresh(evaluation)
    return evaluation


@router.get("/interviews/{interview_id}/evaluations", response_model=list[EvaluationResponse])
def list_evaluations(interview_id: int, db: DbSession, user: CurrentUser):
    interview = db.scalar(select(Interview).where(Interview.id == interview_id, Interview.user_id == user.id))
    if interview is None:
        raise _not_found()
    return list(db.scalars(select(Evaluation).where(Evaluation.interview_id == interview_id).order_by(Evaluation.created_at)))


@router.post(
    "/questions/{question_id}/evaluate",
    response_model=EvaluationResponse,
    status_code=status.HTTP_201_CREATED,
)
def evaluate_question_answer(
    question_id: int,
    db: DbSession,
    user: CurrentUser,
):
    """Evaluate the latest answer using the rule-based evaluator."""

    # Ensure the question belongs to the authenticated user's interview.
    question = db.scalar(
        select(Question)
        .join(Interview, Question.interview_id == Interview.id)
        .where(
            Question.id == question_id,
            Interview.user_id == user.id,
        )
    )

    if question is None:
        raise _not_found()

    # Use the latest answer for this question.
    answer = db.scalar(
        select(Answer)
        .where(Answer.question_id == question.id)
        .order_by(Answer.created_at.desc(), Answer.id.desc())
        .limit(1)
    )

    if answer is None:
        raise HTTPException(
            status_code=400,
            detail="The question has no answer to evaluate",
        )

    # The current data model permits only one evaluation per answer.
    existing = db.scalar(
        select(Evaluation).where(Evaluation.answer_id == answer.id)
    )

    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="This answer already has an evaluation",
        )

    try:
        result = evaluate_answer(
            answer_text=answer.answer_text,
            expected_points=question.expected_points or [],
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    # Semantic embeddings estimate coverage against expected answer criteria.
    # They do not independently verify technical correctness.
    completeness = round(result["coverage_score"] / 10, 2)

    evaluation = Evaluation(
        interview_id=question.interview_id,
        answer_id=answer.id,
        technical_accuracy=None,
        relevance=None,
        completeness=completeness,
        communication=None,
        total_score=result["total_score"],
        strengths=result["strengths"],
        improvements=result["improvements"],
        feedback=result["feedback"],
        evaluator="semantic_embedding_v1",
    )

    db.add(evaluation)
    db.flush()

    evaluations = list(
        db.scalars(
            select(Evaluation).where(
                Evaluation.interview_id == question.interview_id
            )
        )
    )

    interview = db.get(Interview, question.interview_id)
    if interview is not None and evaluations:
        interview.overall_score = round(
            sum(item.total_score for item in evaluations)
            / len(evaluations),
            2,
        )

    db.commit()
    db.refresh(evaluation)

    return evaluation
