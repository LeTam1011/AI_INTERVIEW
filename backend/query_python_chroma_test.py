from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / "data" / "chroma_db"
COLLECTION_NAME = "python_questions_test_v1"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

client = chromadb.PersistentClient(path=str(DB_DIR))
collection = client.get_collection(COLLECTION_NAME)
model = SentenceTransformer(MODEL_NAME)

queries = [
    "What is the difference between Python lists and tuples?",
    "How does Python handle memory management?",
    "What is the difference between Python 2 and Python 3?",
]

for query in queries:
    embedding = model.encode(
        [query],
        normalize_embeddings=True,
    ).tolist()

    result = collection.query(
        query_embeddings=embedding,
        n_results=3,
        include=["documents", "metadatas", "distances"],
    )

    print("\n" + "=" * 70)
    print("QUERY:", query)

    for i, metadata in enumerate(result["metadatas"][0], start=1):
        distance = result["distances"][0][i - 1]
        print(f"\n{i}. {metadata.get('question', '(no question)')}")
        print(f"   Topic: {metadata.get('topic')}")
        print(f"   Distance: {distance:.4f}")
        print(f"   Answer: {metadata.get('answer', '')[:250]}")

print("\nCollection count:", collection.count())
