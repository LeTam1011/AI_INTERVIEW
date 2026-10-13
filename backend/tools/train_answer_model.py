
import csv
import json
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.model_selection import LeaveOneOut, cross_val_predict
from sklearn.metrics import mean_absolute_error


BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_FILE = BACKEND_DIR / "data" / "ml" / "answer_scoring" / "train.csv"
MODEL_DIR = BACKEND_DIR / "models"
MODEL_FILE = MODEL_DIR / "answer_score_model.joblib"
METRICS_FILE = MODEL_DIR / "answer_score_metrics.json"


def load_dataset():
    rows = []

    with DATA_FILE.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            question = row["question_text"].strip()
            expected = row["expected_points"].strip()
            answer = row["answer_text"].strip()
            level = row["career_level"].strip().lower()
            score = float(row["score"])

            # Kết hợp ngữ cảnh câu hỏi với câu trả lời.
            text = (
                f"question: {question} "
                f"expected_points: {expected} "
                f"answer: {answer} "
                f"career_level: {level}"
            )

            rows.append({"text": text, "score": score})

    if len(rows) < 5:
        raise ValueError(
            "Cần ít nhất 5 mẫu hợp lệ để thử nghiệm huấn luyện."
        )

    return rows


def main():
    rows = load_dataset()
    texts = [row["text"] for row in rows]
    scores = [row["score"] for row in rows]

    model = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                lowercase=True,
                strip_accents=None,
                ngram_range=(1, 2),
                sublinear_tf=True,
                max_features=10000,
            ),
        ),
        ("regressor", Ridge(alpha=10.0)),
    ])

    # Leave-one-out chỉ là kiểm tra thăm dò với bộ dữ liệu rất nhỏ.
    cv_predictions = cross_val_predict(
        model,
        texts,
        scores,
        cv=LeaveOneOut(),
    )

    mae = mean_absolute_error(scores, cv_predictions)

    model.fit(texts, scores)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_FILE)

    metrics = {
        "model_type": "TF-IDF + Ridge Regression",
        "training_samples": len(rows),
        "cross_validation": "LeaveOneOut",
        "cross_validation_mae": round(float(mae), 3),
        "warning": (
            "Chỉ có ít dữ liệu minh họa; MAE chưa phản ánh "
            "khả năng tổng quát hóa trên dữ liệu thực tế."
        ),
    }

    METRICS_FILE.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("Huấn luyện hoàn tất.")
    print(f"Số mẫu: {len(rows)}")
    print(f"MAE kiểm tra chéo: {mae:.2f} điểm")
    print(f"Model: {MODEL_FILE}")
    print(f"Metrics: {METRICS_FILE}")


if __name__ == "__main__":
    main()
