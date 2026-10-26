
from typing import Any

from app.ai.question_generator import generate_questions
from app.ai.question_retrieval import search_questions


MIN_SIMILARITY = 0.45
MAX_QUESTIONS_PER_TOPIC = 1


SKILL_QUERY_TEMPLATES = {
    "java": [
        "What is the difference between JDK and JRE?",
        "Explain JVM and Java memory management.",
    ],
    "spring boot": [
        "How does Spring Boot differ from Spring Framework?",
        "Explain dependency injection in Spring.",
    ],
    "spring": [
        "Explain dependency injection in Spring.",
    ],
    "rest api": [
        "How do you design REST APIs?",
    ],
    "git": [
        "How do Git branches and merges work?",
        "What is a merge conflict in Git?",
    ],
    "react": [
        "How do React components manage state?",
        "What are React hooks and when are they used?",
    ],
    "react hooks": [
        "What are React hooks and when are they used?",
    ],
    "javascript": [
        "How does the JavaScript event loop work?",
    ],
    "machine learning": [
        "What is overfitting and underfitting in machine learning?",
        "How do you evaluate a machine learning model?",
    ],
    "model deployment": [
        "How do you deploy a machine learning model?",
    ],
    "docker": [
        "What is Docker and how are containers used?",
    ],
    "data analytics": [
        "How do you clean and explore a dataset?",
    ],
    "pandas": [
        "How do you manipulate data using Pandas?",
    ],
    "python": [
        "Explain Python generators and iterators.",
    ],
    "sql": [
        "Explain SQL joins and database queries.",
    ],
    "oop": [
        "What are the four principles of object-oriented programming?",
    ],
    "object-oriented programming": [
        "What are the four principles of object-oriented programming?",
    ],
    "system design": [
        "How do scalability and availability differ?",
    ],
    "scalability": [
        "How does horizontal scaling improve system capacity?",
    ],
    "availability": [
        "How do redundancy and failover improve availability?",
    ],
}


def build_skill_queries(missing, matched):
    queries = []
    seen = set()

    for skill in missing + matched:
        normalized = str(skill).strip().casefold()

        templates = SKILL_QUERY_TEMPLATES.get(normalized)

        if templates is None:
            templates = [
                f"Explain important concepts and practical uses of {skill}"
            ]

        for query in templates:
            key = query.casefold()

            if key not in seen:
                seen.add(key)
                queries.append(query)

    return queries



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

    
    # Truy vấn kỹ thuật dựa trên các kỹ năng từ CV/JD.
    queries = build_skill_queries(missing, matched)

    # Bổ sung ngữ cảnh công việc sau các truy vấn kỹ thuật.
    if title:
        queries.append(title)

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
    for query in queries[:16]:
        try:
            results = search_questions(
                query,
                top_k=10,
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

    # Nhóm kỹ năng dựa trên metadata và nội dung câu hỏi.
    # Chỉ dùng metadata khi đó là giá trị nhận diện được.
    def get_skill_group(item: dict) -> str:
        category = str(
            item.get("category") or item.get("topic") or ""
        ).casefold()

        question_text = normalize_question(
            item.get("question", "")
        )

        if "javascript" in category:
            return "javascript"

        if category == "java":
            return "java"

        if "react" in category:
            return "react"

        if "spring" in category:
            return "spring"

        if category == "git":
            return "git"

        if "docker" in category:
            return "docker"

        if "machine learning" in category:
            return "machine_learning"

        if "data analytics" in category:
            return "data_analytics"

        if any(x in category for x in (
            "system design", "software design"
        )):
            return "system_design"

        if any(x in question_text for x in (
            "scalability",
            "availability",
            "load balancing",
            "fault tolerance",
        )):
            return "system_design"

        if "oop" in category or "object-oriented" in category:
            return "oop"

        if any(x in question_text for x in (
            "object-oriented",
            "polymorphism",
            "inheritance",
            "encapsulation",
            "abstraction",
        )):
            return "oop"

        if any(x in question_text for x in (
            "sql",
            "sql query",
            "sql queries",
            "sql database",
            "relational database",
            "joins",
            "normalization",
        )):
            return "sql"

        if "sql" in category or "database" in category:
            return "sql"

        if "sql" in question_text:
            return "sql"

        if "python" in category:
            return "python"

        return "other"

    def normalize_skill(skill: str) -> str | None:
        value = str(skill).casefold().strip()

        if any(x in value for x in (
            "system design",
            "software design",
            "scalability",
            "availability",
        )):
            return "system_design"

        if any(x in value for x in (
            "object-oriented",
            "object oriented",
            "oop",
        )):
            return "oop"

        if "sql" in value or "database" in value:
            return "sql"

        if "python" in value:
            return "python"
        
        if "spring" in value:
            return "spring"

        if "javascript" in value:
            return "javascript"

        if "java" in value:
            return "java"

        if "react" in value:
            return "react"

        if "git" in value:
            return "git"

        if "docker" in value:
            return "docker"

        if "machine learning" in value or "model deployment" in value:
            return "machine_learning"

        if "data analytics" in value or "pandas" in value:
            return "data_analytics"

        if "rest api" in value:
            return "rest_api"

        return None

    # Ưu tiên kỹ năng còn thiếu trước, sau đó kỹ năng đã có.
    skill_priority = []

    incompatible_groups = {
        "java": {"javascript"},
        "spring": {"javascript"},
        "react": {"java"},
        "machine_learning": {"javascript"},
    }

    blocked_groups = set()

    for group in skill_priority:
        blocked_groups.update(
            incompatible_groups.get(group, set())
        )

    blocked_groups.difference_update(skill_priority)

    for skill in missing + matched:
        group = normalize_skill(skill)

        if group and group not in skill_priority:
            skill_priority.append(group)

    # Không vượt quá số vị trí còn lại.
    rag_slots = max(0, count - len(questions))

    selected: list[tuple[dict[str, Any], str]] = []
    selected_topics: set[str] = set()
    selected_ids: set[str] = set()

    def add_candidate(item: dict) -> bool:
        question_text = str(
            item.get("question") or ""
        ).strip()

        skill_group = get_skill_group(item)

        if skill_group in blocked_groups:
            return False

        if not question_text:
            return False

        normalized = normalize_question(question_text)
        source_id = str(item.get("id") or "")

        
        skill_group = get_skill_group(item)
        inferred_topic = infer_question_topic(question_text)

        # Chỉ xem là trùng khi cùng nhóm kỹ năng
        # và cùng chủ đề kiến thức.
        topic_key = f"{skill_group}:{inferred_topic}"


        if normalized in seen:
            return False

        if source_id and source_id in selected_ids:
            return False

        if topic_key in selected_topics:
            return False

        selected.append((item, topic_key))
        selected_topics.add(topic_key)

        if source_id:
            selected_ids.add(source_id)

        return True

    # Vòng 1: phân bổ một câu tốt nhất cho mỗi nhóm kỹ năng.
    for skill in skill_priority:
        if len(selected) >= rag_slots:
            break

        for item in ranked:
            if get_skill_group(item) != skill:
                continue

            if add_candidate(item):
                break

    # Vòng 2: bổ sung câu khác, vẫn ưu tiên kỹ năng liên quan.
    for item in ranked:
        if len(selected) >= rag_slots:
            break

        if get_skill_group(item) not in skill_priority:
            continue

        add_candidate(item)

    # Vòng 3: dùng kết quả còn lại nếu vẫn thiếu câu hỏi.
    for item in ranked:
        if len(selected) >= rag_slots:
            break

        add_candidate(item)


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
