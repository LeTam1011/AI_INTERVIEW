from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / "data" / "chroma_db"
COLLECTION_NAME = "python_questions_test_v1"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Các truy vấn đại diện cho những chủ đề Python thường gặp.
TEST_QUERIES = [
    "What is the difference between Python lists and tuples?",
    "How does Python handle memory management and garbage collection?",
    "What is the difference between Python 2 and Python 3?",
    "What is object-oriented programming in Python?",
    "What are decorators in Python and how do they work?",
    "What are generators and the yield keyword in Python?",
    "How does exception handling work in Python?",
    "What is the Global Interpreter Lock (GIL) in Python?",
    "What is list comprehension in Python?",
    "What are lambda functions in Python?",
]


def main():
    client = chromadb.PersistentClient(path=str(DB_DIR))
    names = {item.name for item in client.list_collections()}

    if COLLECTION_NAME not in names:
        raise RuntimeError(
            f"Collection '{COLLECTION_NAME}' not found. "
            "Run test_python_chroma.py first."
        )

    collection = client.get_collection(COLLECTION_NAME)
    model = SentenceTransformer(MODEL_NAME)

    print("Collection:", COLLECTION_NAME)
    print("Total chunks:", collection.count())
    print("Queries:", len(TEST_QUERIES))

    for index, query in enumerate(TEST_QUERIES, start=1):
        vector = model.encode(
            [query],
            normalize_embeddings=True,
            show_progress_bar=False,
        ).tolist()

        result = collection.query(
            query_embeddings=vector,
            n_results=min(5, collection.count()),
            include=["metadatas", "distances"],
        )

        print("\n" + "=" * 78)
        print(f"TEST {index}: {query}")

        questions = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        for rank, (metadata, distance) in enumerate(
            zip(questions, distances), start=1
        ):
            print(f"\n  {rank}. {metadata.get('question', '(missing question)')}")
            print(f"     Distance: {distance:.4f}")
            print(f"     Topic: {metadata.get('topic', 'Unknown')}")

    print("\n" + "=" * 78)
    print("Inspection complete. No database records were modified.")


if __name__ == "__main__":
    main()
