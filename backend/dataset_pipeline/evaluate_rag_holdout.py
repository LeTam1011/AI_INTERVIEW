
import csv
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

BACKEND_DIR = Path(__file__).resolve().parents[1]
DB_DIR = BACKEND_DIR / "dataset_pipeline/data/chroma_db"
OUTPUT = BACKEND_DIR / "dataset_pipeline/rag_holdout_review.csv"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
TOP_K = 5

COLLECTIONS = [
    "software_interview_questions_source_check",
    "software_interview_questions_improved_v2",
]

# Bộ kiểm thử mới, không sử dụng để thiết kế hai chunk bổ sung
TEST_CASES = [
    ("Data Analytics",
     "How can an analyst identify suspicious outliers in a dataset?"),

    ("Docker",
     "Why do Docker images use multiple layers?"),

    ("Git",
     "How can you undo a committed change without rewriting shared history?"),

    ("Java",
     "What happens when the Java garbage collector reclaims memory?"),

    ("JavaScript",
     "How does JavaScript schedule asynchronous callbacks?"),

    ("Machine Learning",
     "How can you detect whether a machine learning model is overfitting?"),

    ("Node.js",
     "Why is non-blocking I/O important for Node.js servers?"),

    ("OOP",
     "How do encapsulation and abstraction serve different purposes?"),

    ("OOP",
     "Can a subclass override behavior while preserving a common interface?"),

    ("Python",
     "When is a Python generator preferable to building a list?"),

    ("React",
     "What causes a React component to render again?"),

    ("Software Design",
     "How would you increase a service's capacity as traffic grows?"),

    ("Software Design",
     "How can an application remain accessible during a server failure?"),

    ("Spring",
     "Why is dependency injection useful in Spring applications?"),

    ("SQL",
     "How can database indexes speed up queries while slowing down writes?"),
]


def main():
    client = chromadb.PersistentClient(path=str(DB_DIR))

    collections = {
        name: client.get_collection(name)
        for name in COLLECTIONS
    }

    expected_counts = {
        COLLECTIONS[0]: 1783,
        COLLECTIONS[1]: 1785,
    }

    for name, collection in collections.items():
        count = collection.count()
        print(f"{name}: {count} records")

        if count != expected_counts[name]:
            raise RuntimeError(
                f"Unexpected count for {name}: {count}"
            )

    model = SentenceTransformer(MODEL_NAME)

    embeddings = model.encode(
        [query for _, query in TEST_CASES],
        normalize_embeddings=True,
        show_progress_bar=False,
    ).tolist()

    rows = []

    for i, ((topic, query), embedding) in enumerate(
        zip(TEST_CASES, embeddings), start=1
    ):
        query_id = f"T{i:02d}"

        for collection_name, collection in collections.items():
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
                rows.append({
                    "query_id": query_id,
                    "topic": topic,
                    "query": query,
                    "collection": collection_name,
                    "rank": rank,
                    "record_id": record_id,
                    "question": metadata.get("question", ""),
                    "answer": metadata.get("answer", ""),
                    "cosine_distance": round(float(distance), 6),
                    "relevant": "",
                })

    expected = len(TEST_CASES) * len(COLLECTIONS) * TOP_K

    if len(rows) != expected:
        raise RuntimeError(
            f"Expected {expected} results, got {len(rows)}"
        )

    with OUTPUT.open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "query_id",
                "topic",
                "query",
                "collection",
                "rank",
                "record_id",
                "question",
                "answer",
                "cosine_distance",
                "relevant",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print("\nHOLDOUT RETRIEVAL COMPLETE")
    print("Queries:", len(TEST_CASES))
    print("Collections:", len(COLLECTIONS))
    print("Results:", len(rows))
    print("Output:", OUTPUT)
    print("Database collections were not modified.")


if __name__ == "__main__":
    main()
