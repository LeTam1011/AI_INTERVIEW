
import re
import unicodedata
from typing import Any

from app.ai.semantic_model import get_semantic_model

FULL_MATCH_THRESHOLD = 0.70
PARTIAL_MATCH_THRESHOLD = 0.55


def normalize_text(text: str) -> str:
    """Chuẩn hóa văn bản để so khớp từ khóa cơ bản."""
    text = (text or "").casefold().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(
        char
        for char in text
        if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"[^a-z0-9+#.]+", " ", text).strip()


def split_answer_sentences(answer: str) -> list[str]:
    """Tách câu trả lời theo dấu câu và xuống dòng."""
    parts = re.split(r"(?<=[.!?])\s+|\n+", answer.strip())
    return [part.strip() for part in parts if part.strip()]


def _score_similarity(similarity: float) -> float:
    """Quy đổi độ tương đồng thành điểm tiêu chí."""
    if similarity >= FULL_MATCH_THRESHOLD:
        return 1.0

    if similarity >= PARTIAL_MATCH_THRESHOLD:
        return 0.5

    return 0.0


def evaluate_answer(
    answer_text: str,
    expected_points: list[str] | None = None,
) -> dict[str, Any]:
    """
    Đánh giá mức độ bao phủ tiêu chí bằng embedding ngữ nghĩa.

    Lưu ý: điểm tương đồng không chứng minh kiến thức đúng
    về mặt kỹ thuật.
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
                "Chưa thể đánh giá vì câu hỏi chưa có tiêu chí "
                "chấm điểm."
            ),
        }

    sentences = split_answer_sentences(answer) or [answer]
    model = get_semantic_model()

    embeddings = model.encode(
        [*sentences, *points],
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    sentence_embeddings = embeddings[:len(sentences)]
    point_embeddings = embeddings[len(sentences):]

    # Mỗi tiêu chí được so sánh với từng câu trả lời.
    similarity_matrix = point_embeddings @ sentence_embeddings.T
    similarities = [
        float(max(row))
        for row in similarity_matrix
    ]

    matched_points = []
    partial_points = []
    missing_points = []
    criterion_scores = []

    for point, similarity in zip(points, similarities):
        score = _score_similarity(similarity)
        criterion_scores.append(score)

        if similarity >= FULL_MATCH_THRESHOLD:
            matched_points.append(point)
        elif similarity >= PARTIAL_MATCH_THRESHOLD:
            partial_points.append(point)
            missing_points.append(point)
        else:
            missing_points.append(point)

    coverage_score = round(
        sum(criterion_scores) / len(points) * 100,
        2,
    )

    # Không cộng điểm chỉ vì câu trả lời dài.
    total_score = coverage_score

    word_count = len(answer.split())
    if word_count < 10:
        total_score = min(total_score, 25.0)

    strengths = []

    if matched_points:
        strengths.append(
            f"Có {len(matched_points)}/{len(points)} tiêu chí "
            "đạt ngưỡng tương đồng cao."
        )

    if partial_points:
        strengths.append(
            f"Có {len(partial_points)} tiêu chí được đề cập "
            "nhưng cần làm rõ thêm."
        )

    improvements = []

    if missing_points:
        improvements.append(
            "Cần bổ sung hoặc làm rõ: "
            + "; ".join(missing_points)
        )

    if word_count < 10:
        improvements.append(
            "Câu trả lời quá ngắn; hãy giải thích rõ hơn "
            "và đưa ví dụ khi phù hợp."
        )

    if total_score >= 80:
        feedback = (
            "Câu trả lời bao phủ tốt các tiêu chí theo độ "
            "tương đồng ngữ nghĩa. Cần kiểm tra thêm tính "
            "chính xác kỹ thuật."
        )
    elif total_score >= 60:
        feedback = (
            "Câu trả lời mới đáp ứng một phần tiêu chí; "
            "hãy bổ sung những nội dung còn thiếu."
        )
    else:
        feedback = (
            "Câu trả lời chưa thể hiện đủ các tiêu chí "
            "được yêu cầu."
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
