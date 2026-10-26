
import csv
from collections import Counter
from pathlib import Path

import app.ai.question_retrieval as retrieval

from dataset_pipeline.rag_question_generator_expanded_test import (
    generate_rag_questions,
)

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_DB_DIR = BACKEND_DIR / "dataset_pipeline/data/chroma_db"

COLLECTION_NAME = "software_interview_questions_improved_v2"

OUTPUT = (
    BACKEND_DIR
    / "dataset_pipeline"
    / "rag_expanded_profiles_results.csv"
)

PROFILES = [
    {
        "name": "Python Backend Intern",
        "level": "intern",
        "title": "Python Backend Developer",
        "description": (
            "Develop REST APIs using Python. "
            "Work with SQL databases and object-oriented design. "
            "Understand scalable and highly available systems."
        ),
        "matched": ["Python", "SQL", "OOP"],
        "missing": ["System Design", "Scalability"],
        "expected": ["Python", "SQL", "OOP", "System Design"],
    },
    {
        "name": "Java Backend Fresher",
        "level": "fresher",
        "title": "Java Backend Developer",
        "description": (
            "Build backend applications using Java and Spring Boot. "
            "Work with SQL, REST APIs and object-oriented programming."
        ),
        "matched": ["Java", "OOP", "SQL"],
        "missing": ["Spring Boot", "REST API"],
        "expected": ["Java", "Spring", "SQL", "OOP"],
    },
    {
        "name": "React Frontend Intern",
        "level": "intern",
        "title": "React Frontend Developer",
        "description": (
            "Build responsive interfaces with React and JavaScript. "
            "Use React hooks, component state and Git."
        ),
        "matched": ["JavaScript", "React"],
        "missing": ["Git", "React Hooks"],
        "expected": ["JavaScript", "React", "Git"],
    },
    {
        "name": "Data Analyst Intern",
        "level": "intern",
        "title": "Data Analyst",
        "description": (
            "Analyze datasets using Python, Pandas and SQL. "
            "Perform data cleaning, statistics and reporting."
        ),
        "matched": ["Python", "SQL"],
        "missing": ["Data Analytics", "Pandas"],
        "expected": ["Python", "SQL", "Data Analytics"],
    },
    {
        "name": "ML Engineer Fresher",
        "level": "fresher",
        "title": "Machine Learning Engineer",
        "description": (
            "Train and evaluate machine learning models "
            "using Python. Understand feature engineering, "
            "overfitting, model deployment and Docker."
        ),
        "matched": ["Python", "Machine Learning"],
        "missing": ["Docker", "Model Deployment"],
        "expected": ["Python", "Machine Learning", "Docker"],
    },
]


def classify_source_topic(source, question):
    """Phân nhóm sơ bộ để báo cáo, không thay đổi generator."""
    category = str(source.get("category") or "").casefold()
    text = str(question).casefold()

    if "docker" in category:
        return "Docker"
    if "git" in category:
        return "Git"
    if "react" in category:
        return "React"
    if "javascript" in category:
        return "JavaScript"
    if "spring" in category:
        return "Spring"
    if "java" in category:
        return "Java"
    if "machine learning" in category:
        return "Machine Learning"
    if "data analytics" in category:
        return "Data Analytics"
    if "software design" in category or "system design" in category:
        return "System Design"
    if "oop" in category or "object-oriented" in category:
        return "OOP"
    if "sql" in category:
        return "SQL"
    if "python" in category:
        return "Python"

    if "scalability" in text or "availability" in text:
        return "System Design"

    return "Other"


def build_context(profile):
    return {
        "career_level": profile["level"],
        "job": {
            "title": profile["title"],
            "description": profile["description"],
        },
        "cv_score": {
            "matched_required_skills": profile["matched"],
            "missing_required_skills": profile["missing"],
        },
    }


def main():
    original_dir = retrieval.CHROMA_DIR
    original_test_name = retrieval.PYTHON_TEST_COLLECTION_NAME

    rows = []

    try:
        retrieval.CHROMA_DIR = TEST_DB_DIR
        retrieval.PYTHON_TEST_COLLECTION_NAME = COLLECTION_NAME
        retrieval.get_collection.cache_clear()

        collection = retrieval.get_collection(COLLECTION_NAME)

        if collection.count() != 1785:
            raise RuntimeError(
                f"Unexpected collection size: {collection.count()}"
            )

        for profile in PROFILES:
            questions = generate_rag_questions(
                context_snapshot=build_context(profile),
                count=10,
                collection_name=COLLECTION_NAME,
            )

            print("\n" + "=" * 85)
            print("PROFILE:", profile["name"])
            print("EXPECTED SKILLS:", ", ".join(profile["expected"]))

            rag_topics = Counter()
            rag_count = 0

            for position, item in enumerate(questions, start=1):
                source = item.get("source_context") or {}
                is_rag = source.get("source") == "rag"

                question = str(item.get("question_text") or "")
                group = (
                    classify_source_topic(source, question)
                    if is_rag else "BASE"
                )

                if is_rag:
                    rag_count += 1
                    rag_topics[group] += 1

                print(
                    f"{position:2}. "
                    f"[{'RAG' if is_rag else 'BASE'}] "
                    f"[{group}] {question}"
                )

                rows.append({
                    "profile": profile["name"],
                    "position": position,
                    "source_type": "RAG" if is_rag else "BASE",
                    "skill_group": group,
                    "question": question,
                    "source_id": source.get("source_id", ""),
                    "similarity": source.get("similarity", ""),
                    "review": "",
                })

            covered = set(rag_topics)
            missing = [
                skill
                for skill in profile["expected"]
                if skill not in covered
            ]

            print("\nTOTAL:", len(questions))
            print("RAG:", rag_count)
            print("BASE:", len(questions) - rag_count)
            print("RAG TOPICS:", dict(rag_topics))
            print("EXPECTED SKILLS NOT COVERED BY RAG:", missing)

        with OUTPUT.open(
            "w", encoding="utf-8-sig", newline=""
        ) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "profile",
                    "position",
                    "source_type",
                    "skill_group",
                    "question",
                    "source_id",
                    "similarity",
                    "review",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

        print("\n" + "=" * 85)
        print("TEST COMPLETED")
        print("Total questions:", len(rows))
        print("Output:", OUTPUT)
        print("No production data was modified.")

    finally:
        retrieval.CHROMA_DIR = original_dir
        retrieval.PYTHON_TEST_COLLECTION_NAME = original_test_name
        retrieval.get_collection.cache_clear()


if __name__ == "__main__":
    main()
