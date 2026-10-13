import json
import sys
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


BACKEND_DIR = Path(__file__).resolve().parents[1]
CHUNK_DIR = BACKEND_DIR / "dataset_pipeline" / "data" / "chunk"
CHROMA_DIR = BACKEND_DIR / "data" / "chroma_db"

COLLECTION_NAME = "software_interview_questions"
NEW_COLLECTION_NAME = f"{COLLECTION_NAME}_new"
OLD_COLLECTION_NAME = f"{COLLECTION_NAME}_old"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 64


def load_chunks() -> list[dict]:
    """Đọc và kiểm tra dữ liệu chunks từ các file JSON."""
    chunks = []

    for path in sorted(CHUNK_DIR.glob("chunked_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))

        if not isinstance(data, list):
            raise ValueError(
                f"{path.name}: JSON root must be a list"
            )

        for chunk in data:
            question = str(chunk.get("question", "")).strip()
            answer = str(chunk.get("answer", "")).strip()
            content = str(chunk.get("content", "")).strip()
            metadata = chunk.get("metadata") or {}

            if not question or not content:
                raise ValueError(
                    f"Invalid chunk in {path.name}: "
                    f"{chunk.get('id', 'unknown')}"
                )

            chunk_id = str(chunk.get("id", "")).strip()

            if not chunk_id:
                raise ValueError(
                    f"Missing chunk ID in {path.name}"
                )

            chunk_metadata = {
                "question": question,
                "topic": str(
                    metadata.get("topic", "General")
                ),
                "difficulty": str(
                    metadata.get("difficulty", "Unknown")
                ),
                "type": str(
                    metadata.get("type", "technical")
                ),
                "source": str(
                    metadata.get("source", path.name)
                ),
                "answer_status": str(
                    metadata.get(
                        "answer_status",
                        "available" if answer else "pending",
                    )
                ),
            }

            # Chỉ lưu answer khi có nội dung.
            if answer:
                chunk_metadata["answer"] = answer

            chunks.append({
                "id": chunk_id,
                "document": content,
                "metadata": chunk_metadata,
            })

    if not chunks:
        raise RuntimeError(
            f"No chunks found in {CHUNK_DIR}"
        )

    ids = [chunk["id"] for chunk in chunks]

    if len(ids) != len(set(ids)):
        raise ValueError(
            "Duplicate chunk IDs detected"
        )

    return chunks


def create_new_collection(client, chunks, model):
    """Tạo collection mới và nạp toàn bộ dữ liệu."""
    # Xóa collection _new còn sót lại từ lần chạy trước.
    try:
        client.delete_collection(NEW_COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=NEW_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start:start + BATCH_SIZE]

        documents = [
            item["document"] for item in batch
        ]

        embeddings = model.encode(
            documents,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).tolist()

        collection.add(
            ids=[item["id"] for item in batch],
            documents=documents,
            metadatas=[
                item["metadata"] for item in batch
            ],
            embeddings=embeddings,
        )

        indexed = min(
            start + len(batch),
            len(chunks),
        )

        print(f"Indexed {indexed}/{len(chunks)}")

    actual_count = collection.count()

    if actual_count != len(chunks):
        raise RuntimeError(
            f"Expected {len(chunks)} records, "
            f"got {actual_count}"
        )

    return collection


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

    # Mặc định chỉ kiểm tra, không sửa database.
    if "--apply" not in sys.argv:
        print("DRY RUN: database has not been changed.")
        print(
            "Review the data, then run with --apply "
            "to replace it."
        )
        return

    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )

    try:
        model = SentenceTransformer(
            EMBEDDING_MODEL
        )

        new_collection = create_new_collection(
            client,
            chunks,
            model,
        )

        print(
            f"Validated new collection: "
            f"{new_collection.count()} records."
        )

        replace_collection(client)

    except Exception:
        print(
            "Import failed. Inspect the collection names "
            "before retrying. The old collection is retained "
            "when the replacement process has reached its "
            "backup step."
        )
        raise


if __name__ == "__main__":
    main()