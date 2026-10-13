
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

BACKEND_DIR = Path(__file__).resolve().parents[1]
CHROMA_DIR = BACKEND_DIR / "data" / "chroma_db"

COLLECTION_NAME = "software_interview_questions"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

TEST_QUERIES = [
    "Explain object-oriented programming and its four principles",
    "How do SQL joins combine data from multiple tables?",
    "Explain JavaScript closures and lexical scope",
    "What is Docker and why is it useful?",
]


def main():
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )

    collection = client.get_collection(
        name=COLLECTION_NAME
    )

    print(f"Tổng số câu hỏi: {collection.count()}")

    model = SentenceTransformer(EMBEDDING_MODEL)

    for query in TEST_QUERIES:
        query_embedding = model.encode(
            [query],
            normalize_embeddings=True,
        ).tolist()

        results = collection.query(
            query_embeddings=query_embedding,
            n_results=5,
            include=["metadatas", "distances"],
        )

        print("\n" + "=" * 80)
        print(f"TRUY VẤN: {query}")
        print("-" * 80)

        ids = results["ids"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for rank, (item_id, metadata, distance) in enumerate(
            zip(ids, metadatas, distances),
            start=1,
        ):
            similarity = 1 - distance

            print(f"\n{rank}. {metadata['question']}")
            print(f"   ID: {item_id}")
            print(f"   Category: {metadata['category']}")
            print(f"   Difficulty: {metadata['difficulty']}")
            print(f"   Cosine similarity: {similarity:.4f}")
            print(f"   Answer: {metadata['answer'][:250]}")


if __name__ == "__main__":
    main()
