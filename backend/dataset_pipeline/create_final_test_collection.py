import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent
CHUNK_DIR = BASE_DIR / "data" / "chunk_final_test"
CHROMA_DIR = BASE_DIR / "data" / "chroma_db"
COLLECTION_NAME = "software_interview_questions_final_test"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 64


def main():
    files = sorted(CHUNK_DIR.glob("chunked_*.json"))

    if len(files) != 13:
        raise RuntimeError(
            f"Expected 13 JSON files, found {len(files)}"
        )

    records = []
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, list):
            raise ValueError(f"Invalid JSON structure: {path.name}")
        records.extend(data)

    if len(records) != 1783:
        raise RuntimeError(f"Expected 1783 records, got {len(records)}")

    ids = [str(r.get("id", "")).strip() for r in records]
    if any(not x for x in ids) or len(ids) != len(set(ids)):
        raise ValueError("Missing or duplicate IDs")

    documents = []
    metadatas = []

    for record in records:
        question = str(record.get("question", "")).strip()
        answer = str(record.get("answer", "")).strip()
        content = str(record.get("content", "")).strip()

        if not question or not answer:
            raise ValueError(f"Empty question/answer: {record.get('id')}")

        expected = f"Question: {question}\n\nAnswer: {answer}"
        if content != expected:
            raise ValueError(f"Content mismatch: {record.get('id')}")

        meta = record.get("metadata") or {}
        documents.append(content)
        metadatas.append({
            "question": question,
            "answer": answer,
            "topic": str(meta.get("topic", "General")),
            "difficulty": str(meta.get("difficulty", "Unknown")),
            "type": str(meta.get("type", "technical")),
            "source": str(meta.get("source", "")),
            "answer_status": str(meta.get("answer_status", "available")),
        })

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    existing = {c.name for c in client.list_collections()}

    if COLLECTION_NAME in existing:
        raise RuntimeError(
            f"Collection already exists: {COLLECTION_NAME}. "
            "Nothing was changed; do not delete it automatically."
        )

    print("Validated records:", len(records))
    print("Loading embedding model:", MODEL_NAME)
    model = SentenceTransformer(MODEL_NAME)

    print("Computing embeddings...")
    embeddings = model.encode(
        documents,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    created = False
    try:
        collection = client.create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        created = True

        for start in range(0, len(records), BATCH_SIZE):
            end = min(start + BATCH_SIZE, len(records))
            collection.add(
                ids=ids[start:end],
                documents=documents[start:end],
                metadatas=metadatas[start:end],
                embeddings=embeddings[start:end].tolist(),
            )
            print(f"Inserted {end}/{len(records)}")

        actual = client.get_collection(COLLECTION_NAME)
        if actual.count() != len(records):
            raise RuntimeError(
                f"Count mismatch: expected {len(records)}, "
                f"got {actual.count()}"
            )

        print("\nCOLLECTION CREATED SUCCESSFULLY")
        print("Name:", COLLECTION_NAME)
        print("Count:", actual.count())
        print("Embedding model:", MODEL_NAME)
        print("Distance: cosine")
        print("Production collection: unchanged")

    except Exception:
        if created:
            try:
                client.delete_collection(COLLECTION_NAME)
                print("Removed incomplete collection created by this run.")
            except Exception as cleanup_error:
                print("WARNING: cleanup failed:", cleanup_error)
        raise


if __name__ == "__main__":
    main()
