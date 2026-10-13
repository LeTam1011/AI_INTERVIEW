
import re
import unicodedata
from typing import Any


def _normalize(text: str) -> str:
    """Normalize text for simple keyword matching."""
    text = (text or "").casefold().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(
        char for char in text
        if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"\s+", " ", text).strip()


def generate_follow_up(
    question_text: str,
    answer_text: str,
    expected_points: list[str] | None = None,
    topic: str | None = None,
    language: str = "vi",
    evaluation_score: float | None = None,
    evaluation_hint: str | None = None,
) -> dict[str, Any]:
    """
    Generate one follow-up question using deterministic rules.
    No external AI API is used.
    """

    original_question = (question_text or "").strip()
    answer = (answer_text or "").strip()
    points = [
        point.strip()
        for point in (expected_points or [])
        if isinstance(point, str) and point.strip()
    ]
    topic_name = (topic or "nội dung vừa trao đổi").strip()

    normalized_answer = _normalize(answer)
    word_count = len(answer.split())

    
    # 1. Empty or repetitive answers must be handled first.
    words = re.findall(r"\b[\w+#.]+\b", normalized_answer)
    unique_words = set(words)

    repetitive = (
        len(words) >= 5
        and len(unique_words) <= 2
    )

    if not answer or not normalized_answer or repetitive:
        follow_up_text = (
            f"Bạn có thể trả lời lại câu hỏi "
            f"'{original_question}' bằng kiến thức của mình "
            "và đưa ra một ví dụ cụ thể không?"
        )
        reason = "Câu trả lời chưa cung cấp đủ thông tin hữu ích."

    else:
        missing_points = [
            point for point in points
            if _normalize(point) not in normalized_answer
        ]

        # 2. Prioritize a low evaluation score.
        if evaluation_score is not None and evaluation_score < 60:
            if missing_points:
                focus = missing_points[0]
                follow_up_text = (
                    f"Trong câu trả lời về {topic_name}, "
                    f"bạn hãy làm rõ nội dung: {focus}. "
                    "Hãy giải thích cách áp dụng và đưa ra ví dụ."
                )
                reason = (
                    "Điểm đánh giá thấp, cần làm rõ tiêu chí còn thiếu."
                )
            else:
                follow_up_text = (
                    f"Bạn hãy giải thích từng bước khi xử lý "
                    f"một vấn đề liên quan đến {topic_name}, "
                    "kèm ví dụ và kết quả mong đợi."
                )
                reason = (
                    "Điểm đánh giá thấp, cần củng cố câu trả lời."
                )

        # 3. High score: ask a deeper question.
        elif evaluation_score is not None and evaluation_score >= 80:
            follow_up_text = (
                f"Dựa trên câu trả lời về {topic_name}, "
                "hãy phân tích một tình huống phức tạp hơn: "
                "nếu giải pháp không đạt kết quả mong muốn, "
                "bạn sẽ xác định nguyên nhân và cải thiện thế nào?"
            )
            reason = (
                "Điểm đánh giá tốt, chuyển sang câu hỏi đào sâu."
            )

        # 4. Short answers without a low/high score.
        elif len(answer.split()) < 15:
            follow_up_text = (
                f"Bạn hãy giải thích rõ hơn về {topic_name}, "
                "nêu cách bạn thực hiện và đưa ra một ví dụ cụ thể."
            )
            reason = (
                "Câu trả lời ngắn, cần giải thích và ví dụ."
            )

        # 5. Medium score or no evaluation.
        elif missing_points:
            focus = missing_points[0]
            follow_up_text = (
                f"Bạn có thể làm rõ nội dung '{focus}' "
                f"trong câu trả lời về {topic_name} không?"
            )
            reason = (
                "Làm rõ tiêu chí chưa được đề cập rõ."
            )

        else:
            follow_up_text = (
                f"Dựa trên câu trả lời về {topic_name}, "
                "bạn sẽ xử lý thế nào nếu giải pháp gặp hạn chế "
                "hoặc không đạt kết quả mong muốn?"
            )
            reason = (
                "Đào sâu khả năng áp dụng và xử lý tình huống."
            )

    return {
        "question_text": follow_up_text,
        "question_type": "follow_up",
        "topic": topic_name[:120],
        "expected_points": [
            "Giải thích rõ ràng và có lập luận",
            "Đưa ra ví dụ hoặc tình huống cụ thể",
            "Nêu cách đánh giá kết quả hoặc xử lý vấn đề",
        ],
        "source_context": {
            "original_question": original_question,
            "answer_excerpt": answer[:500],
            "reason": reason,
            "generator": "rule_based_v2",
            "evaluation_score": evaluation_score,
            "evaluation_hint": evaluation_hint,
        },
    }