
import json
from pathlib import Path

import joblib

BACKEND_DIR = Path(__file__).resolve().parents[1]
MODEL_FILE = BACKEND_DIR / "models" / "answer_score_model.joblib"
METRICS_FILE = BACKEND_DIR / "models" / "answer_score_metrics.json"


def predict_score(
    model,
    question: str,
    expected_points: str,
    answer: str,
    career_level: str = "intern",
) -> float:
    text = (
        f"question: {question} "
        f"expected_points: {expected_points} "
        f"answer: {answer} "
        f"career_level: {career_level.lower()}"
    )

    prediction = float(model.predict([text])[0])

    # Giữ điểm trong khoảng 0–100.
    return round(max(0.0, min(100.0, prediction)), 2)


def main():
    if not MODEL_FILE.exists():
        raise FileNotFoundError(
            f"Không tìm thấy model: {MODEL_FILE}"
        )

    model = joblib.load(MODEL_FILE)

    if METRICS_FILE.exists():
        metrics = json.loads(
            METRICS_FILE.read_text(encoding="utf-8")
        )
        print("Thông tin huấn luyện:")
        print(json.dumps(metrics, ensure_ascii=False, indent=2))

    question = "REST API là gì?"
    expected_points = (
        "giao tiếp giữa client và server; "
        "HTTP methods; "
        "JSON; "
        "HTTP status codes"
    )

    test_answers = [
        (
            "Câu trả lời ngắn",
            "REST API là cách để các ứng dụng giao tiếp với nhau."
        ),
        (
            "Câu trả lời chi tiết",
            "REST API cho phép client giao tiếp với server "
            "thông qua HTTP. GET dùng để lấy dữ liệu, POST "
            "dùng để tạo dữ liệu, PUT hoặc PATCH dùng để cập nhật, "
            "DELETE dùng để xóa. Dữ liệu thường được trao đổi "
            "dưới dạng JSON và server trả về HTTP status code "
            "để biểu thị kết quả của yêu cầu."
        ),
        (
            "Câu trả lời không liên quan",
            "Em thích chơi game và nghe nhạc vào cuối tuần."
        ),
    ]

    print("\nKẾT QUẢ DỰ ĐOÁN")
    print("-" * 60)

    for label, answer in test_answers:
        score = predict_score(
            model=model,
            question=question,
            expected_points=expected_points,
            answer=answer,
        )

        print(f"{label}: {score}/100")

    print("-" * 60)
    print("Hoàn tất kiểm tra model.")


if __name__ == "__main__":
    main()
