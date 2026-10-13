import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent
JSON_PATH = BASE_DIR / "dataset_pipeline" / "data" / "chunk" / "test_chunked_python_interview_question.json"
CHROMA_DIR = BASE_DIR / "data" / "chroma_db"

COLLECTION_NAME = "python_questions_test_v1"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 32


def main():
    chunks = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    if len(chunks) != 267:
        raise ValueError(f"Expected 267 chunks, got {len(chunks)}")

    ids = [str(c["id"]) for c in chunks]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate IDs detected")

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    existing = {c.name for c in client.list_collections()}

    # Do not overwrite an existing collection.
    if COLLECTION_NAME in existing:
        raise RuntimeError(
            f"Collection {COLLECTION_NAME} already exists. "
            "Nothing was changed."
        )

    model = SentenceTransformer(MODEL_NAME)
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    try:
        for start in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[start:start + BATCH_SIZE]
            documents = []
            metadatas = []

            for chunk in batch:
                question = str(chunk.get("question", "")).strip()
                answer = str(chunk.get("answer", "")).strip()
                content = str(chunk.get("content", "")).strip()
                source_metadata = chunk.get("metadata") or {}

                if not question or not answer or not content:
                    raise ValueError(
                        f"Missing question, answer or content: {chunk.get('id')}"
                    )

                metadata = {
                    "question": question,
                    "answer": answer,
                    "topic": str(source_metadata.get("topic", "Python")),
                    "difficulty": str(
                        source_metadata.get("difficulty", "Unknown")
                    ),
                    "type": str(
                        source_metadata.get("type", "technical")
                    ),
                    "source": str(
                        source_metadata.get("source", JSON_PATH.name)
                    ),
                    "answer_status": "available",
                }

                documents.append(content)
                metadatas.append(metadata)

            embeddings = model.encode(
                documents,
                normalize_embeddings=True,
                show_progress_bar=False,
            ).tolist()

            collection.add(
                ids=[str(c["id"]) for c in batch],
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
            )

            print(
                f"Inserted {min(start + len(batch), len(chunks))}"
                f"/{len(chunks)}"
            )

        actual_count = collection.count()
        if actual_count != len(chunks):
            raise RuntimeError(
                f"Expected {len(chunks)} records, got {actual_count}"
            )

        print("\nSUCCESS")
        print("Collection:", COLLECTION_NAME)
        print("Expected records:", len(chunks))
        print("Actual records:", actual_count)
        print("Existing production collection was not renamed or deleted.")

    except Exception:
        # Remove only this newly created test collection if ingestion fails.
        client.delete_collection(COLLECTION_NAME)
        raise


if __name__ == "__main__":
    main()
