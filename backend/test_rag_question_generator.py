
from app.ai.rag_question_generator import generate_rag_questions

context = {
    "candidate_profile": {
        "skills": ["Python", "SQL"]
    },
    "resume_text": (
        "Developed REST APIs using Python and FastAPI. "
        "Worked with PostgreSQL and basic data structures."
    ),
    "cv_score": {
        "matched_required_skills": ["Python", "SQL"],
        "missing_required_skills": ["Decorators", "Generators"],
    },
    "job": {
        "title": "Python Backend Developer Intern",
        "description": (
            "Develop REST APIs with Python and FastAPI. "
            "Understand decorators, generators, SQL and REST."
        ),
        "required_skills": ["Python", "FastAPI", "SQL"],
        "preferred_skills": [],
        "responsibilities": ["Develop and test backend APIs"],
    },
    "career_level": "intern",
    "language": "en",
}

questions = generate_rag_questions(
    context_snapshot=context,
    count=5,
    collection_name="python_questions_test_v1",
)

print(f"\nTotal questions: {len(questions)}")

for i, item in enumerate(questions, start=1):
    print(f"\n{i}. {item['question_text']}")
    print(f"Topic: {item.get('topic')}")
    print(f"Source: {(item.get('source_context') or {}).get('source')}")
    print(f"Similarity: {(item.get('source_context') or {}).get('similarity')}")
