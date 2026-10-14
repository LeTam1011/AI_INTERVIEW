import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


BACKEND_DIR = Path(__file__).resolve().parents[1]
CHUNK_DIR = (
    BACKEND_DIR
    / "dataset_pipeline"
    / "data"
    / "chunk_clean_test"
)
CHROMA_DIR = BACKEND_DIR / "data" / "chroma_db"

COLLECTION_NAME = "software_interview_questions_clean_test_v3"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 64


def main():
    files = sorted(CHUNK_DIR.glob("chunked_*.json"))

    if not files:
        raise RuntimeError(f"No chunked JSON files found in {CHUNK_DIR}")

    chunks = []

    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))

        if not isinstance(data, list):
            raise ValueError(f"{path.name}: JSON root must be a list")

        for item in data:
            question = str(item.get("question", "")).strip()
            answer = str(item.get("answer", "")).strip()
            content = str(item.get("content", "")).strip()
            chunk_id = str(item.get("id", "")).strip()
            metadata = item.get("metadata") or {}

            if not question or not content or not chunk_id:
                raise ValueError(f"Invalid chunk in {path.name}: {chunk_id}")

            chunk_metadata = {
                "question": question,
                "topic": str(metadata.get("topic", "General")),
                "difficulty": str(metadata.get("difficulty", "Unknown")),
                "type": str(metadata.get("type", "technical")),
                "source": str(metadata.get("source", path.name)),
                "answer_status": str(
                    metadata.get(
                        "answer_status",
                        "available" if answer else "pending",
                    )
                ),
            }

            if answer:
                chunk_metadata["answer"] = answer

            chunks.append({
                "id": chunk_id,
                "document": content,
                "metadata": chunk_metadata,
            })

    ids = [item["id"] for item in chunks]

    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate chunk IDs detected")

    if len(chunks) != 1783:
        raise ValueError(
            f"Expected 1783 chunks, got {len(chunks)}. Aborting."
        )

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    existing_names = {c.name for c in client.list_collections()}

    if COLLECTION_NAME in existing_names:
        raise RuntimeError(
            f"{COLLECTION_NAME} already exists. Refusing to overwrite it."
        )

    print(f"Source files: {len(files)}")
    print(f"Chunks validated: {len(chunks)}")
    print(f"Target collection: {COLLECTION_NAME}")

    model = SentenceTransformer(EMBEDDING_MODEL)

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    try:
        for start in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[start:start + BATCH_SIZE]

            embeddings = model.encode(
                [item["document"] for item in batch],
                normalize_embeddings=True,
                show_progress_bar=False,
            ).tolist()

            collection.add(
                ids=[item["id"] for item in batch],
                documents=[item["document"] for item in batch],
                metadatas=[item["metadata"] for item in batch],
                embeddings=embeddings,
            )

            print(f"Indexed {min(start + len(batch), len(chunks))}/{len(chunks)}")

        actual_count = collection.count()

        if actual_count != 1783:
            raise RuntimeError(
                f"Expected 1783 records, got {actual_count}"
            )

        print(f"\nSuccess: {COLLECTION_NAME} contains {actual_count} records.")

    except Exception:
        print(
            "\nImport failed. The test collection may be incomplete. "
            "It has not been renamed to the production collection."
        )
        raise


if __name__ == "__main__":
    main()



