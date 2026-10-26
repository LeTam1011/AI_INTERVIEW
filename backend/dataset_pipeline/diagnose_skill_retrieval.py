
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

BACKEND_DIR = Path(__file__).resolve().parents[1]
DB_DIR = BACKEND_DIR / "dataset_pipeline/data/chroma_db"
COLLECTION_NAME = "software_interview_questions_improved_v2"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MIN_SIMILARITY = 0.45

TEST_CASES = {
    "Java": [
        "Java programming technical interview",
        "What are important Java core concepts?",
    ],
    "Git": [
        "Git programming technical interview",
        "How do Git branches and merges work?",
    ],
    "Machine Learning": [
        "Machine Learning programming technical interview",
        "How do you prevent overfitting in machine learning?",
    ],
}

def main():
    client = chromadb.PersistentClient(path=str(DB_DIR))
    collection = client.get_collection(COLLECTION_NAME)
    model = SentenceTransformer(MODEL_NAME)

    for skill, queries in TEST_CASES.items():
        print("\n" + "=" * 80)
        print("SKILL:", skill)

        for query in queries:
            embedding = model.encode(
                [query],
                normalize_embeddings=True,
                show_progress_bar=False,
            ).tolist()

            result = collection.query(
                query_embeddings=embedding,
                n_results=10,
                include=["metadatas", "distances"],
            )

            print("\nQUERY:", query)

            for rank, (record_id, metadata, distance) in enumerate(
                zip(
                    result["ids"][0],
                    result["metadatas"][0],
                    result["distances"][0],
                ),
                start=1,
            ):
                similarity = 1 - float(distance)
                status = (
                    "PASS"
                    if similarity >= MIN_SIMILARITY
                    else "FAIL"
                )

                print(
                    f"{rank:2}. [{status}] "
                    f"sim={similarity:.4f} "
                    f"topic={metadata.get('topic', '')}"
                )
                print(
                    "    ID:", record_id
                )
                print(
                    "    Q:", metadata.get("question", "")
                )

    print("\nDiagnostic complete. Database unchanged.")

if __name__ == "__main__":
    main()
