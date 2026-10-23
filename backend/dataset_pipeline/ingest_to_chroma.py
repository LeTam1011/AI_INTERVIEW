import json
import sys
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


BACKEND_DIR = Path(__file__).resolve().parents[1]

CHUNK_DIR = BACKEND_DIR / "dataset_pipeline" / "data" / "chunk"

# Chỉ dùng để tạo và kiểm tra collection thử nghiệm.
TEST_CHROMA_DIR = (
    BACKEND_DIR / "dataset_pipeline" / "data" / "chroma_db"
)

TEST_COLLECTION_NAME = "software_interview_questions_final_test"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 64


def load_chunks() -> list[dict]:
    """Đọc chunks, giữ nguyên nội dung nguồn và không loại câu trả lời ngắn."""
    chunks = []

    for path in sorted(CHUNK_DIR.glob("chunked_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))

        if not isinstance(data, list):
            raise ValueError(
                f"{path.name}: JSON root must be a list"
            )

        for chunk in data:
            question = str(chunk.get("question", ""))
            answer = str(chunk.get("answer", ""))
            content = str(chunk.get("content", ""))
            chunk_id = str(chunk.get("id", "")).strip()
            metadata = chunk.get("metadata") or {}

            if not question.strip() or not content.strip():
                raise ValueError(
                    f"Invalid chunk in {path.name}: "
                    f"{chunk.get('id', 'unknown')}"
                )

            if not chunk_id:
                raise ValueError(
                    f"Missing chunk ID in {path.name}"
                )

            chunk_metadata = {
                "question": question,
                "topic": str(metadata.get("topic", "General")),
                "difficulty": str(
                    metadata.get("difficulty", "Unknown")
                ),
                "type": str(metadata.get("type", "technical")),
                "source": str(metadata.get("source", path.name)),
                "answer_status": str(
                    metadata.get(
                        "answer_status",
                        "available" if answer.strip() else "pending",
                    )
                ),
            }

            # Giữ nguyên answer, không yêu cầu độ dài tối thiểu.
            if answer.strip():
                chunk_metadata["answer"] = answer

            chunks.append({
                "id": chunk_id,
                "document": content,
                "metadata": chunk_metadata,
            })

    if not chunks:
        raise RuntimeError(f"No chunks found in {CHUNK_DIR}")

    ids = [chunk["id"] for chunk in chunks]

    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate chunk IDs detected")

    return chunks


def create_test_collection(client, chunks, model):
    """Tạo collection thử nghiệm mới, không ghi đè collection cũ."""

    existing_names = {
        item.name for item in client.list_collections()
    }

    if TEST_COLLECTION_NAME in existing_names:
        raise RuntimeError(
            f"Collection {TEST_COLLECTION_NAME} already exists. "
            "No data was changed. Inspect it before retrying."
        )

    collection = client.create_collection(
        name=TEST_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    try:
        for start in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[start:start + BATCH_SIZE]

            documents = [item["document"] for item in batch]
            embeddings = model.encode(
                documents,
                normalize_embeddings=True,
                show_progress_bar=False,
            ).tolist()

            collection.add(
                ids=[item["id"] for item in batch],
                documents=documents,
                metadatas=[item["metadata"] for item in batch],
                embeddings=embeddings,
            )

            print(
                f"Indexed {min(start + len(batch), len(chunks))}"
                f"/{len(chunks)}"
            )

        if collection.count() != len(chunks):
            raise RuntimeError(
                f"Expected {len(chunks)} records, "
                f"got {collection.count()}"
            )

        print(
            f"Test collection created: {collection.name}, "
            f"{collection.count()} records."
        )
        return collection

    except Exception:
        # Không tự xóa collection lỗi để tránh mất dữ liệu
        # và giúp kiểm tra nguyên nhân trước khi xử lý tiếp.
        print(
            "Collection creation failed. "
            "Inspect the test collection before retrying."
        )
        raise


def replace_collection(client):
    """Thay collection chính nhưng giữ nguyên dữ liệu cũ."""

    collection_names = {
        item.name for item in client.list_collections()
    }

    if NEW_COLLECTION_NAME not in collection_names:
        raise RuntimeError(
            f"Collection {NEW_COLLECTION_NAME} does not exist"
        )

    new_collection = client.get_collection(
        NEW_COLLECTION_NAME
    )
    expected_count = new_collection.count()

    if expected_count != 1783:
        raise RuntimeError(
            f"Expected 1783 new chunks, got {expected_count}. "
            "Refusing to replace the current collection."
        )

    if COLLECTION_NAME not in collection_names:
        raise RuntimeError(
            f"Current collection {COLLECTION_NAME} is missing."
        )

    # Giữ collection chính hiện tại dưới tên archive riêng.
    # Collection software_interview_questions_old (174 records)
    # được giữ nguyên, không đổi tên hoặc xóa.
    archive_name = f"{COLLECTION_NAME}_archive_1810"

    if archive_name in collection_names:
        raise RuntimeError(
            f"Archive {archive_name} already exists. "
            "Inspect collections before retrying."
        )

    current_collection = client.get_collection(
        COLLECTION_NAME
    )

    current_count = current_collection.count()
    if current_count != 1810:
        raise RuntimeError(
            f"Expected 1810 current records, got {current_count}. "
            "Refusing to replace the current collection."
        )

    # Đổi tên collection hiện tại để bảo toàn dữ liệu.
    current_collection.modify(name=archive_name)
    print(f"Preserved current collection as {archive_name}")

    try:
        # Chuyển collection mới thành collection chính.
        new_collection.modify(name=COLLECTION_NAME)

    except Exception:
        # Nếu đổi tên collection mới thất bại, khôi phục tên cũ.
        client.get_collection(archive_name).modify(
            name=COLLECTION_NAME
        )
        print("Restored the original collection name.")
        raise

    final_collection = client.get_collection(COLLECTION_NAME)
    actual_count = final_collection.count()

    if actual_count != expected_count:
        raise RuntimeError(
            f"Expected {expected_count} records after replacement, "
            f"got {actual_count}. Inspect collections before retrying."
        )

    print(
        f"Success: {COLLECTION_NAME} now contains "
        f"{actual_count} records."
    )
    print(f"Previous collection preserved as {archive_name}.")
    print(
        f"Existing backup {OLD_COLLECTION_NAME} "
        "was left unchanged."
    )


def main():
    chunks = load_chunks()
    print(f"Loaded {len(chunks)} chunks.")

    # Mặc định chỉ kiểm tra dữ liệu nguồn.
    if "--build-test" not in sys.argv:
        print("DRY RUN: no database was modified.")
        print("Use --build-test to create a separate test collection.")
        return

    client = chromadb.PersistentClient(
        path=str(TEST_CHROMA_DIR)
    )

    model = SentenceTransformer(EMBEDDING_MODEL)

    create_test_collection(client, chunks, model)


if __name__ == "__main__":
    main()
