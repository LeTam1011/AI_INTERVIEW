
from typing import Any

from app.ai.question_generator import generate_questions
from app.ai.question_retrieval import search_questions


MIN_SIMILARITY = 0.45
MAX_QUESTIONS_PER_TOPIC = 1


def normalize_question(text: str) -> str:
    """Normalize question text for exact duplicate detection."""
    return " ".join(str(text or "").casefold().split())


def infer_question_topic(question: str) -> str:
    """Infer a more specific topic from question content."""
    text = normalize_question(question)

    
    # Nhận diện các nhóm kỹ thuật cụ thể trước
    # khi xét các nhóm từ khóa chung.

    if (
        "four pillars" in text
        or "four main principles" in text
        or "four principles" in text
    ):
        return "oop_core_principles"

    if "scalability" in text or "availability" in text:
        return "system_scalability_availability"

    if (
        "load balancing" in text
        or "fault tolerance" in text
        or "high availability" in text
    ):
        return "system_reliability"

    if (
        "design patterns" in text
        or "design pattern" in text
    ):
        return "software_design_patterns"


    topic_keywords = {
        "decorators": ["decorator"],
        "generators": ["generator", "yield"],
        "exception_handling": [
            "exception", "error handling", "custom exception",
            "try-except", "try except",
        ],
        "object_oriented": [
            "object oriented", "inheritance", "polymorphism",
            "abstract base class", "abcs",
        ],
        "data_structures": [
            "list comprehension", "dictionary", "tuple",
            "list", "set",
        ],
        "database": [
            "database", "sql", "postgresql", "sqlite", "orm",
        ],
        "web_api": [
            "fastapi", "rest api", "restful", "http request",
            "requests library", "api endpoint",
        ],
        "concurrency": [
            "thread", "process", "asyncio", "async", "concurrency",
        ],
        "debugging": [
            "debug", "debugging", "find bugs", "find errors",
            "traceback",
        ],
    }

    for topic, keywords in topic_keywords.items():
        if any(keyword in text for keyword in keywords):
            return topic

    return "general_python"


def generate_rag_questions(
    context_snapshot: dict[str, Any],
    count: int = 10,
    collection_name: str = "software_interview_questions",
) -> list[dict[str, Any]]:
    """Combine CV-based questions with diverse RAG questions."""

    if count <= 0:
        return []

    context = context_snapshot or {}
    job = context.get("job") or {}
    cv_score = context.get("cv_score") or {}

    level = str(context.get("career_level", "intern")).lower()
    missing = cv_score.get("missing_required_skills") or []
    matched = cv_score.get("matched_required_skills") or []

    title = str(job.get("title") or "").strip()
    description = str(job.get("description") or "").strip()

    # Reserve approximately 40% for questions based on interview context.
    base_count = max(1, count * 2 // 5)

    questions = list(
        generate_questions(
            context_snapshot=context,
            count=base_count,
        )
    )[:count]

    seen = {
        normalize_question(item.get("question_text", ""))
        for item in questions
        if item.get("question_text")
    }

    # Record topics already covered by baseline questions.
    seen_topics = {
        infer_question_topic(item.get("question_text", ""))
        for item in questions
        if item.get("question_text")
    }

    if len(questions) >= count:
        for position, item in enumerate(questions, start=1):
            item["position"] = position
        return questions[:count]

    queries: list[str] = []

    if title:
        queries.append(title)

    for skill in missing + matched:
        skill = str(skill).strip()
        if skill:
            queries.append(
                f"{skill} programming technical interview"
            )

    if description:
        queries.append(description[:500])

    if not queries:
        fallback = generate_questions(
            context_snapshot=context,
            count=count,
        )
        return fallback[:count]

    candidates: dict[str, dict[str, Any]] = {}

    # Retrieve candidates from the requested collection.
    for query in queries[:8]:
        try:
            results = search_questions(
                query,
                top_k=5,
                collection_name=collection_name,
            )
        except (RuntimeError, ValueError):
            continue

        for result in results:
            question_text = str(
                result.get("question") or ""
            ).strip()

            try:
                similarity = float(result.get("similarity") or 0)
            except (TypeError, ValueError):
                continue

            if not question_text or similarity < MIN_SIMILARITY:
                continue

            normalized = normalize_question(question_text)

            if normalized in seen:
                continue

            previous = candidates.get(normalized)
            if (
                previous is None
                or similarity > previous["similarity"]
            ):
                candidates[normalized] = {
                    **result,
                    "question": question_text,
                    "similarity": similarity,
                }

    ranked = sorted(
        candidates.values(),
        key=lambda item: item["similarity"],
        reverse=True,
    )

    # Prefer topics not already covered by baseline questions.
    selected: list[tuple[dict[str, Any], str]] = []
    selected_topics: set[str] = set()

    for item in ranked:
        question_text = str(item.get("question") or "").strip()
        topic = infer_question_topic(question_text)

        if not question_text:
            continue

        if normalize_question(question_text) in seen:
            continue

        if topic in selected_topics:
            continue

        selected.append((item, topic))
        selected_topics.add(topic)

    # Add diverse RAG questions.
    for item, inferred_topic in selected:
        if len(questions) >= count:
            break

        question_text = str(item.get("question") or "").strip()
        normalized = normalize_question(question_text)

        if not question_text or normalized in seen:
            continue

        answer = str(item.get("answer") or "").strip()
        category = str(item.get("category") or "").strip()

        questions.append({
            "position": len(questions) + 1,
            "question_text": question_text,
            "question_type": "technical",
            "topic": inferred_topic[:120],
            "expected_points": [answer] if answer else [
                "Explain the concept and how it works",
                "Give a relevant practical example",
                "Discuss limitations and edge cases",
            ],
            "source_context": {
                "reason": (
                    "Retrieved from the local interview question database"
                ),
                "source": "rag",
                "source_id": item.get("id"),
                "category": category or None,
                "difficulty": item.get("difficulty"),
                "similarity": item.get("similarity"),
                "career_level": level,
                "job_title": title,
                "language": "en",
            },
        })

        seen.add(normalized)
        seen_topics.add(inferred_topic)

    # Fill any remaining slots with baseline-generated questions.
    if len(questions) < count:
        fallback = generate_questions(
            context_snapshot=context,
            count=count,
        )

        for item in fallback:
            if len(questions) >= count:
                break

            question_text = str(
                item.get("question_text") or ""
            ).strip()
            normalized = normalize_question(question_text)

            if not question_text or normalized in seen:
                continue

            topic = infer_question_topic(question_text)

            if topic in seen_topics:
                continue

            questions.append({
                **item,
                "position": len(questions) + 1,
            })

            seen.add(normalized)
            seen_topics.add(topic)

    # If topic diversity prevents reaching count, fill remaining slots
    # with unique questions rather than returning too few questions.
    if len(questions) < count:
        for item in fallback if "fallback" in locals() else []:
            if len(questions) >= count:
                break

            question_text = str(
                item.get("question_text") or ""
            ).strip()
            normalized = normalize_question(question_text)

            if not question_text or normalized in seen:
                continue

            questions.append({
                **item,
                "position": len(questions) + 1,
            })
            seen.add(normalized)

    for position, item in enumerate(questions[:count], start=1):
        item["position"] = position

    return questions[:count]
