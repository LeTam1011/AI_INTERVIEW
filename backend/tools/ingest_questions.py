
import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

BACKEND_DIR = Path(__file__).resolve().parents[1]

DATA_FILE = (
    BACKEND_DIR
    / "data"
    / "processed"
    / "software_questions.jsonl"
)

CHROMA_DIR = BACKEND_DIR / "data" / "chroma_db"
COLLECTION_NAME = "software_interview_questions"

# Mô hình embedding nhẹ, chạy cục bộ.
# Lần đầu có thể cần Internet để tải mô hình.
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def load_questions():
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Không tìm thấy dữ liệu: {DATA_FILE}"
        )

    questions = []

    with DATA_FILE.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"JSON lỗi tại dòng {line_number}"
                ) from exc

            required = [
                "id",
                "question",
                "answer",
                "category",
                "difficulty",
                "text",
            ]

            missing = [
                key for key in required
                if not item.get(key)
            ]

            if missing:
                raise ValueError(
                    f"Dòng {line_number} thiếu trường: {missing}"
                )

            questions.append(item)

    if not questions:
        raise ValueError("Không có câu hỏi để nạp.")

    return questions


def main():
    questions = load_questions()

    print(f"Số câu hỏi đọc được: {len(questions)}")
    print("Đang tải mô hình embedding...")

    model = SentenceTransformer(EMBEDDING_MODEL)

    print("Đang tạo embedding...")
    documents = [item["text"] for item in questions]

    embeddings = model.encode(
        documents,
        normalize_embeddings=True,
        show_progress_bar=True,
    ).tolist()

    print("Đang kết nối ChromaDB...")

    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )

    # Dùng tên collection riêng; không xóa collection khác.
    # Xóa collection cùng tên để tránh dữ liệu cũ bị trùng
    # khi chạy lại script.
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    batch_size = 50

    for start in range(0, len(questions), batch_size):
        batch_questions = questions[
            start:start + batch_size
        ]
        batch_embeddings = embeddings[
            start:start + batch_size
        ]

        collection.add(
            ids=[item["id"] for item in batch_questions],
            documents=[
                item["text"] for item in batch_questions
            ],
            embeddings=batch_embeddings,
            metadatas=[
                {
                    "question": item["question"],
                    "category": item["category"],
                    "difficulty": item["difficulty"],
                    "answer": item["answer"],
                }
                for item in batch_questions
            ],
        )

    print("\n=== NẠP DỮ LIỆU HOÀN TẤT ===")
    print(f"Số câu hỏi: {collection.count()}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Database: {CHROMA_DIR}")


if __name__ == "__main__":
    main()
