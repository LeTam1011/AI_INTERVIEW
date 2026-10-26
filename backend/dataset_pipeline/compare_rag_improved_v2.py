
import csv
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from dataset_pipeline.build_rag_review_set import TEST_CASES

BACKEND_DIR = Path(__file__).resolve().parents[1]
PIPELINE_DIR = BACKEND_DIR / "dataset_pipeline"

DB_DIR = PIPELINE_DIR / "data" / "chroma_db"
COLLECTION_NAME = "software_interview_questions_improved_v2"

BASELINE_CSV = PIPELINE_DIR / "rag_review_candidates.csv"
OUTPUT_CSV = PIPELINE_DIR / "rag_review_improved_v2.csv"

TOP_K = 5

def main():
    if not BASELINE_CSV.exists():
        raise FileNotFoundError(
            f"Baseline CSV not found: {BASELINE_CSV}"
        )

    old_labels = {}

    with BASELINE_CSV.open(
        "r", encoding="utf-8-sig", newline=""
    ) as f:
        for row in csv.DictReader(f):
            label = row["relevant"].strip()

            if label not in {"0", "1"}:
                continue

            key = (
                row["query_id"],
                row["record_id"],
            )
            old_labels[key] = label

    client = chromadb.PersistentClient(path=str(DB_DIR))
    collection = client.get_collection(COLLECTION_NAME)

    if collection.count() != 1785:
        raise RuntimeError("Unexpected collection size")

    model = SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2"
    )

    queries = [query for _, query in TEST_CASES]

    embeddings = model.encode(
        queries,
        normalize_embeddings=True,
        show_progress_bar=False,
    ).tolist()

    rows = []
    reused = 0
    new_results = 0

    for i, ((topic, query), embedding) in enumerate(
        zip(TEST_CASES, embeddings), start=1
    ):
        query_id = f"Q{i:02d}"

        result = collection.query(
            query_embeddings=[embedding],
            n_results=TOP_K,
            include=["metadatas", "distances"],
        )

        for rank, (record_id, metadata, distance) in enumerate(
            zip(
                result["ids"][0],
                result["metadatas"][0],
                result["distances"][0],
            ),
            start=1,
        ):
            key = (query_id, record_id)
            label = old_labels.get(key, "")

            if label:
                reused += 1
            else:
                new_results += 1

            rows.append({
                "query_id": query_id,
                "topic": topic,
                "query": query,
                "rank": rank,
                "record_id": record_id,
                "question": metadata.get("question", ""),
                "cosine_distance": round(float(distance), 6),
                "relevant": label,
            })

    if len(rows) != len(TEST_CASES) * TOP_K:
        raise RuntimeError("Unexpected number of results")

    with OUTPUT_CSV.open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "query_id", "topic", "query", "rank",
                "record_id", "question",
                "cosine_distance", "relevant",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print("Output:", OUTPUT_CSV)
    print("Total results:", len(rows))
    print("Reused labels:", reused)
    print("Results requiring review:", new_results)

if __name__ == "__main__":
    main()
