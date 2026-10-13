
import re
import unicodedata
from typing import Any


STOP_WORDS = {
    "va", "la", "cua", "cho", "voi", "mot", "cac", "nhung",
    "duoc", "trong", "khi", "thi", "se", "da", "co", "can",
    "the", "de", "tu", "nay", "do", "neu", "hay", "hon",
    "a", "an", "the",
}


def normalize_text(text: str) -> str:
    """Normalize Vietnamese text for keyword matching."""
    text = (text or "").casefold().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(
        char for char in text
        if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"[^a-z0-9+#.]+", " ", text).strip()


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in normalize_text(text).split()
        if token not in STOP_WORDS and len(token) > 1
    }


def _criterion_coverage(answer: str, criterion: str) -> float:
    """
    Estimate lexical coverage of a criterion.
    This is keyword matching, not semantic understanding.
    """
    normalized_answer = normalize_text(answer)
    normalized_criterion = normalize_text(criterion)

    if not normalized_criterion:
        return 0.0

    # Preserve exact phrase matches as a strong signal.
    if normalized_criterion in normalized_answer:
        return 1.0

    criterion_tokens = _tokens(criterion)
    answer_tokens = _tokens(answer)

    if not criterion_tokens:
        return 0.0

    return len(criterion_tokens & answer_tokens) / len(criterion_tokens)


def evaluate_answer(
    answer_text: str,
    expected_points: list[str] | None = None,
) -> dict[str, Any]:
    """
    Rule-based answer evaluation using criterion keyword coverage.
    This is not a semantic AI evaluator.
    """
    answer = (answer_text or "").strip()

    if not answer:
        raise ValueError("Answer text cannot be empty")

    points = [
        point.strip()
        for point in (expected_points or [])
        if isinstance(point, str) and point.strip()
    ]

    if not points:
        return {
            "total_score": 0.0,
            "coverage_score": 0.0,
            "matched_points": [],
            "missing_points": [],
            "strengths": [],
            "improvements": [
                "Chưa có tiêu chí expected_points để đánh giá câu trả lời."
            ],
            "feedback": (
                "Chưa thể đánh giá mức độ đáp ứng nội dung vì câu hỏi "
                "chưa có tiêu chí chấm điểm."
            ),
        }

    matched_points = []
    missing_points = []
    partial_points = []

    for point in points:
        coverage = _criterion_coverage(answer, point)

        if coverage >= 0.6:
            matched_points.append(point)
        else:
            missing_points.append(point)
            if coverage >= 0.3:
                partial_points.append(point)

    # Award partial credit for criteria that are partly covered.
    point_scores = []
    for point in points:
        coverage = _criterion_coverage(answer, point)
        point_scores.append(
            1.0 if coverage >= 0.6
            else coverage if coverage >= 0.3
            else 0.0
        )

    coverage_score = round(
        sum(point_scores) / len(points) * 100,
        2,
    )

    # Length is used only as a small completeness signal.
    word_count = len(answer.split())

    if word_count >= 25:
        detail_score = 100
    elif word_count >= 10:
        detail_score = 70
    else:
        detail_score = 40

    total_score = round(
        coverage_score * 0.9 + detail_score * 0.1,
        2,
    )

    strengths = []
    if matched_points:
        strengths.append(
            f"Đáp ứng tốt {len(matched_points)}/{len(points)} "
            "tiêu chí theo mức độ trùng khớp từ khóa."
        )
    if partial_points:
        strengths.append(
            f"Đã đề cập một phần {len(partial_points)} tiêu chí."
        )

    improvements = []
    if missing_points:
        improvements.append(
            "Cần bổ sung hoặc làm rõ: "
            + "; ".join(missing_points)
        )
    if word_count < 10:
        improvements.append(
            "Câu trả lời ngắn; nên giải thích rõ hơn và đưa ví dụ."
        )

    if total_score >= 80:
        feedback = (
            "Câu trả lời đáp ứng tốt các tiêu chí theo bộ so khớp hiện tại."
        )
    elif total_score >= 60:
        feedback = (
            "Câu trả lời đáp ứng một phần; cần bổ sung các ý còn thiếu."
        )
    else:
        feedback = (
            "Câu trả lời còn thiếu nhiều nội dung theo tiêu chí hiện tại."
        )

    return {
        "total_score": total_score,
        "coverage_score": coverage_score,
        "matched_points": matched_points,
        "missing_points": missing_points,
        "strengths": strengths,
        "improvements": improvements,
        "feedback": feedback,
    }
