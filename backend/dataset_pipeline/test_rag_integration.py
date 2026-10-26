
from pathlib import Path

import app.ai.question_retrieval as retrieval
from dataset_pipeline.rag_question_generator_skill_test import (
    generate_rag_questions,
)

BACKEND_DIR = Path(__file__).resolve().parents[1]

TEST_DB_DIR = (
    BACKEND_DIR / "dataset_pipeline" / "data" / "chroma_db"
)

COLLECTIONS = [
    "software_interview_questions_source_check",
    "software_interview_questions_improved_v2",
]

CONTEXT = {
    "career_level": "intern",
    "job": {
        "title": "Python Backend Developer",
        "description": (
            "Develop backend APIs using Python. "
            "Apply object-oriented programming principles. "
            "Build scalable and highly available services. "
            "Understand SQL, Docker and system design."
        ),
    },
    "cv_score": {
        "matched_required_skills": [
            "Python",
            "Object-Oriented Programming",
            "SQL",
        ],
        "missing_required_skills": [
            "System Design",
            "Scalability",
            "Availability",
        ],
    },
}


def main():
    original_db_dir = retrieval.CHROMA_DIR
    original_test_name = retrieval.PYTHON_TEST_COLLECTION_NAME

    try:
        # Chỉ thay đổi cấu hình trong tiến trình kiểm thử.
        retrieval.CHROMA_DIR = TEST_DB_DIR

        for collection_name in COLLECTIONS:
            retrieval.PYTHON_TEST_COLLECTION_NAME = collection_name
            retrieval.get_collection.cache_clear()

            collection = retrieval.get_collection(collection_name)

            print("\n" + "=" * 80)
            print("COLLECTION:", collection_name)
            print("RECORDS:", collection.count())

            # Kiểm tra semantic search qua hàm thực tế của app.
            for query in [
                "What are the four main principles of OOP?",
                "What is the difference between scalability and availability?",
            ]:
                results = retrieval.search_questions(
                    query=query,
                    top_k=5,
                    collection_name=collection_name,
                )

                print("\nSEARCH:", query)

                for rank, item in enumerate(results, 1):
                    print(
                        f"{rank}. "
                        f"[{item['similarity']:.4f}] "
                        f"{item['id']} | {item['question']}"
                    )

            # Kiểm tra hàm tạo câu hỏi thực tế.
            questions = generate_rag_questions(
                context_snapshot=CONTEXT,
                count=10,
                collection_name=collection_name,
            )

            print("\nGENERATED QUESTIONS:", len(questions))

            rag_count = 0

            for item in questions:
                source = item.get("source_context") or {}
                is_rag = source.get("source") == "rag"

                if is_rag:
                    rag_count += 1

                print(
                    f"{item.get('position', '?')}. "
                    f"[{'RAG' if is_rag else 'BASE'}] "
                    f"{item.get('question_text', '')}"
                )

                if is_rag:
                    print(
                        "   SOURCE ID:",
                        source.get("source_id"),
                    )

            print("RAG QUESTIONS:", rag_count)
            print("BASE QUESTIONS:", len(questions) - rag_count)
            print("\nSKILL COVERAGE:")

            for item in questions:
                source = item.get("source_context") or {}

                if source.get("source") != "rag":
                    continue

                text = item.get("question_text", "").lower()

                if "sql" in text:
                    skill = "SQL"
                elif any(x in text for x in (
                    "scalability", "availability",
                    "load balancing", "fault tolerance"
                )):
                    skill = "System Design"
                elif any(x in text for x in (
                    "object-oriented", "polymorphism",
                    "inheritance", "encapsulation"
                )):
                    skill = "OOP"
                elif "python" in text:
                    skill = "Python"
                else:
                    skill = "Other"

                print(
                    f"- {skill}: {item.get('question_text', '')}"
                )

    finally:
        retrieval.CHROMA_DIR = original_db_dir
        retrieval.PYTHON_TEST_COLLECTION_NAME = original_test_name
        retrieval.get_collection.cache_clear()


if __name__ == "__main__":
    main()
