from pathlib import Path
import csv

import chromadb
from sentence_transformers import SentenceTransformer

BACKEND_DIR = Path(__file__).resolve().parents[1]
CHROMA_DIR = BACKEND_DIR / "dataset_pipeline" / "data" / "chroma_db"
COLLECTION_NAME = "software_interview_questions_source_check"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
TOP_K = 5

TEST_CASES = [
    ("Data Analytics", "What is the difference between mean, median, and mode?"),
    ("Data Analytics", "How would you handle missing values in a dataset?"),
    ("Data Analytics", "What is the difference between correlation and causation?"),

    ("Docker", "What is the difference between a Docker image and a container?"),
    ("Docker", "What is the purpose of a Dockerfile?"),
    ("Docker", "How do Docker volumes persist data?"),

    ("Git", "What is the difference between git merge and git rebase?"),
    ("Git", "How do you resolve a merge conflict in Git?"),
    ("Git", "What is the difference between git fetch and git pull?"),

    ("Java", "What is the difference between JDK, JRE, and JVM?"),
    ("Java", "What is the difference between an interface and an abstract class in Java?"),
    ("Java", "How does exception handling work in Java?"),

    ("JavaScript", "What is the difference between let, const, and var?"),
    ("JavaScript", "What is the difference between == and === in JavaScript?"),
    ("JavaScript", "How do promises and async/await work in JavaScript?"),

    ("Machine Learning", "What is the difference between supervised and unsupervised learning?"),
    ("Machine Learning", "What is the difference between gradient descent and stochastic gradient descent?"),
    ("Machine Learning", "What is overfitting and how can it be prevented?"),

    ("Node.js", "What is the event loop in Node.js?"),
    ("Node.js", "What is the difference between synchronous and asynchronous operations in Node.js?"),
    ("Node.js", "How does Node.js handle modules?"),

    ("OOP", "What are the four main principles of object-oriented programming?"),
    ("OOP", "What is the difference between inheritance and composition?"),
    ("OOP", "What is polymorphism in object-oriented programming?"),

    ("Python", "What is the difference between a list and a tuple in Python?"),
    ("Python", "What are Python decorators and when are they used?"),
    ("Python", "What is the difference between shallow copy and deep copy?"),

    ("React", "What is useEffect and when should it be used?"),
    ("React", "What is the difference between props and state in React?"),
    ("React", "Why are keys important when rendering lists in React?"),

    ("Software Design", "What is the difference between monolithic and microservices architecture?"),
    ("Software Design", "What is the purpose of common software design patterns?"),
    ("Software Design", "What is the difference between scalability and availability?"),

    ("Spring", "How does dependency injection work in Spring Boot?"),
    ("Spring", "What is the difference between @Component, @Service, and @Repository?"),
    ("Spring", "What is the role of Spring Boot auto-configuration?"),

    ("SQL", "What is the difference between INNER JOIN and LEFT JOIN?"),
    ("SQL", "What is the difference between WHERE and HAVING in SQL?"),
    ("SQL", "What is database normalization and why is it useful?"),
]


def main():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    names = {c.name for c in client.list_collections()}
    if COLLECTION_NAME not in names:
        raise RuntimeError(
            f"Missing test collection: {COLLECTION_NAME}. "
            "No collection was modified."
        )

    collection = client.get_collection(COLLECTION_NAME)
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Records: {collection.count()}")

    model = SentenceTransformer(MODEL_NAME)
    output_path = BACKEND_DIR / "dataset_pipeline" / "rag_review_candidates.csv"

    rows = []

    for index, (topic, query) in enumerate(TEST_CASES, start=1):
        vector = model.encode(
            query,
            normalize_embeddings=True,
        ).tolist()

        result = collection.query(
            query_embeddings=[vector],
            n_results=min(TOP_K, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        for rank, (record_id, document, metadata, distance) in enumerate(
            zip(
                result["ids"][0],
                result["documents"][0],
                result["metadatas"][0],
                result["distances"][0],
            ),
            start=1,
        ):
            rows.append({
                "query_id": f"Q{index:02d}",
                "topic": topic,
                "query": query,
                "rank": rank,
                "record_id": record_id,
                "question": metadata.get("question") or document,
                "cosine_distance": round(float(distance), 6),
                "relevant": "",
            })

    with output_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=[
            "query_id", "topic", "query", "rank",
            "record_id", "question", "cosine_distance", "relevant",
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Queries: {len(TEST_CASES)}")
    print(f"Candidates: {len(rows)}")
    print(f"Review CSV: {output_path}")
    print("Read-only: no collection was modified.")


if __name__ == "__main__":
    main()
