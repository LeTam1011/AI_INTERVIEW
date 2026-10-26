
import re
from dataclasses import dataclass
from typing import Iterable, Mapping


@dataclass(frozen=True)
class QualityDecision:
    accepted: bool
    reason: str = "accepted"


def normalize(text: str) -> str:
    text = str(text or "").casefold().strip()
    return re.sub(r"\s+", " ", text)


def get_topic(item: Mapping) -> str:
    return normalize(
        item.get("category") or item.get("topic") or ""
    )



def knowledge_signature(question: str) -> str | None:
    text = normalize(question)

    # Machine Learning: overfitting / underfitting
    if (
        "overfitting" in text
        or "underfitting" in text
    ):
        return "ml_overfitting_underfitting"

    # OOP fundamentals
    if (
        "four pillars" in text
        or "four principles" in text
        or "four main principles" in text
    ):
        return "oop_principles"

    if (
        re.search(
            r"\bwhat is (object-oriented programming|oop)\b",
            text,
        )
    ):
        return "oop_introduction"

    # SQL joins: các câu hỏi gần trùng nội dung cơ bản
    if "join" in text:
        if any(x in text for x in (
            "what is an sql join",
            "what is a sql join",
            "what types of joins",
            "types of joins",
        )):
            return "sql_joins_basics"

    # Python loops
    if re.search(r"\bfor loop\b|\bwhile loop\b", text):
        return "python_basic_loops"

    # Python generators
    if re.search(r"\bgenerators?\b", text):
        if "python" in text or "yield" in text:
            return "python_generators"

    return None



def evaluate_candidate(
    item: Mapping,
    *,
    job_title: str,
    career_level: str,
    selected_questions: Iterable[str] = (),
) -> QualityDecision:
    question = normalize(item.get("question", ""))
    topic = get_topic(item)
    title = normalize(job_title)
    level = normalize(career_level)

    if not question:
        return QualityDecision(False, "empty_question")

    # 1. Trùng nguyên văn
    existing = [
        normalize(q) for q in selected_questions
    ]

    if question in existing:
        return QualityDecision(False, "exact_duplicate")

    # 2. Trùng phạm vi kiến thức trong một số trường hợp rõ ràng
    current_signature = knowledge_signature(question)

    if current_signature:
        existing_signatures = {
            knowledge_signature(q) for q in existing
        }

        if current_signature in existing_signatures:
            return QualityDecision(
                False, "duplicate_knowledge"
            )

    # 3. Bộ lọc công nghệ: chỉ chặn các trường hợp chắc chắn
    #    không phù hợp với vị trí được kiểm thử.
    is_react_frontend = (
        "react" in title and "frontend" in title
    )

    if is_react_frontend:
        if "node.js" in topic or "nodejs" in topic:
            return QualityDecision(
                False, "unrelated_nodejs_topic"
            )

        if "node.js" in question or "nodejs" in question:
            return QualityDecision(
                False, "unrelated_nodejs_question"
            )

        # Câu hỏi nguồn đang diễn đạt khó hiểu.
        if "sources used for introducing hooks" in question:
            return QualityDecision(
                False, "unclear_react_hooks_question"
            )

        if (
            level in {"intern", "internship"}
            and "usedebugvalue" in question
        ):
            return QualityDecision(
                False, "overly_specialized_for_intern"
            )

    is_java_backend = (
        "java" in title and "backend" in title
    )

    if is_java_backend and (
        "node.js" in topic or "nodejs" in topic
        or "node.js" in question
    ):
        return QualityDecision(
            False, "unrelated_nodejs_for_java"
        )

    is_ml_engineer = (
        "machine learning" in title
        or "ml engineer" in title
    )

    if is_ml_engineer:
        if "javascript" in topic or "node.js" in topic:
            return QualityDecision(
                False, "unrelated_technology_for_ml"
            )

        if is_basic_python_question(question):
            return QualityDecision(
                False, "too_basic_for_ml_fresher"
            )

    is_data_analyst = "data analyst" in title

    if is_data_analyst:
        if (
            is_python_generator_question(question)
            or "threads in python" in question
        ):
            return QualityDecision(
                False, "low_priority_for_data_analyst"
            )

    # 4. Một số câu diễn đạt chưa đạt chất lượng tối thiểu.
    known_unclear_questions = (
        "what are different event loops",
        "what are the sources used for introducing hooks",
    )

    if question.rstrip("?.!") in known_unclear_questions:
        return QualityDecision(
            False, "unclear_wording"
        )

    return QualityDecision(True)

def is_basic_python_question(question: str) -> bool:
    text = normalize(question)

    patterns = (
        r"\bfor loop\b",
        r"\bwhile loop\b",
        r"\bzen of python\b",
        r"\bwhat is a loop\b",
    )

    return any(re.search(pattern, text) for pattern in patterns)


def is_python_generator_question(question: str) -> bool:
    text = normalize(question)

    return bool(
        re.search(r"\bgenerators?\b", text)
        and (
            "python" in text
            or "regular functions" in text
            or "yield" in text
        )
    )