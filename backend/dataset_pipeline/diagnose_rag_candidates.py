
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

BACKEND_DIR = Path(__file__).resolve().parents[1]
DB_DIR = BACKEND_DIR / "dataset_pipeline/data/chroma_db"
COLLECTION = "software_interview_questions_improved_v2"

TARGET_IDS = {
    "oop_interview_question-core-principles",
    "sd_interview_question-scalability-availability",
}

TITLE = "Python Backend Developer"

MISSING = [
    "System Design",
    "Scalability",
    "Availability",
]

MATCHED = [
    "Python",
    "Object-Oriented Programming",
    "SQL",
]

DESCRIPTION = (
    "Develop backend APIs using Python. "
    "Apply object-oriented programming principles. "
    "Build scalable and highly available services. "
    "Understand SQL, Docker and system design."
)

# Tái hiện cách tạo queries trong rag_question_generator.py
queries = [TITLE]

for skill in MISSING + MATCHED:
    queries.append(
        f"{skill} programming technical interview"
    )

queries.append(DESCRIPTION[:500])

# Generator chỉ xét 8 queries đầu
queries = queries[:8]

client = chromadb.PersistentClient(path=str(DB_DIR))
collection = client.get_collection(COLLECTION)

model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)

embeddings = model.encode(
    queries,
    normalize_embeddings=True,
    show_progress_bar=False,
).tolist()

for i, (query, embedding) in enumerate(
    zip(queries, embeddings), start=1
):
    print("\n" + "=" * 80)
    print(f"QUERY {i}: {query}")

    result = collection.query(
        query_embeddings=[embedding],
        n_results=20,
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
        similarity = 1 - float(distance)

        if rank <= 5 or record_id in TARGET_IDS:
            selected = "TOP-5" if rank <= 5 else "OUTSIDE TOP-5"
            threshold = (
                "PASS" if similarity >= 0.45 else "FAIL"
            )

            print(
                f"{rank:2}. [{selected}] "
                f"[{threshold}] "
                f"sim={similarity:.4f} "
                f"{record_id}"
            )

    ids = result["ids"][0]

    for target_id in TARGET_IDS:
        if target_id not in ids:
            print(
                f"NOT IN TOP-20: {target_id}"
            )

print("\nDiagnostic complete. Database unchanged.")
