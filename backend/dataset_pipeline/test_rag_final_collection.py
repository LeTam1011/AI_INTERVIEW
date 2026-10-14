
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


# ==================== CONFIG ====================

BACKEND_DIR = Path(__file__).resolve().parents[1]

PRODUCTION_CHROMA_DIR = BACKEND_DIR / "data" / "chroma_db"
TEST_CHROMA_DIR = BACKEND_DIR / "dataset_pipeline" / "data" / "chroma_db"

PRODUCTION_COLLECTION = "software_interview_questions"
TEST_COLLECTION = "software_interview_questions_final_test"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
TOP_K = 5
BATCH_SIZE = 200

TEST_QUERIES = [
    ("Python", "What is the difference between a list and a tuple in Python?"),
    ("Java", "Explain the difference between JDK, JRE, and JVM."),
    ("React", "What is the useEffect hook and when should it be used?"),
    ("SQL", "Explain the difference between INNER JOIN and LEFT JOIN."),
    ("Docker", "What is the difference between a Docker image and a container?"),
    ("Git", "What is the difference between git merge and git rebase?"),
    ("Spring", "How does dependency injection work in Spring Boot?"),
    (
        "Machine Learning",
        "Explain the difference between gradient descent and stochastic gradient descent.",
    ),
]


# ==================== HELPERS ====================

def get_question(metadata, document):
    if metadata:
        for key in ("question", "question_text", "title"):
            value = metadata.get(key)
            if value:
                return str(value)

    return document or "(No document)"


def get_all_ids(collection, batch_size=BATCH_SIZE):
    """Lay toan bo ID, khong tai embedding."""
    ids = []
    total = collection.count()

    for offset in range(0, total, batch_size):
        result = collection.get(
            limit=batch_size,
            offset=offset,
            include=["metadatas"],
        )
        ids.extend(result["ids"])

    return ids



def diagnose_all_records(production, test):
    """So sanh toan bo noi dung, metadata va embedding cua hai collection."""
    import numpy as np

    print("\n" + "=" * 75)
    print("DETAILED COLLECTION DIAGNOSTICS")
    print("=" * 75)

    batch_size = 100
    total = production.count()

    prod_ids = set(get_all_ids(production, batch_size))
    test_ids = set(get_all_ids(test, batch_size))

    common_ids = sorted(prod_ids & test_ids)
    only_prod = prod_ids - test_ids
    only_test = test_ids - prod_ids

    doc_diff = 0
    metadata_diff = 0
    embedding_diff = 0
    embedding_diff_same_doc = 0
    embedding_diff_changed_doc = 0

    details_printed = 0
    max_details = 30

    for offset in range(0, len(common_ids), batch_size):
        batch_ids = common_ids[offset:offset + batch_size]

        p = production.get(
            ids=batch_ids,
            include=["documents", "metadatas", "embeddings"],
        )
        t = test.get(
            ids=batch_ids,
            include=["documents", "metadatas", "embeddings"],
        )

        p_map = {rid: i for i, rid in enumerate(p["ids"])}
        t_map = {rid: i for i, rid in enumerate(t["ids"])}

        for rid in batch_ids:
            i = p_map[rid]
            j = t_map[rid]

            pd = (p["documents"] or [None] * len(p["ids"]))[i]
            td = (t["documents"] or [None] * len(t["ids"]))[j]
            pm = (p["metadatas"] or [None] * len(p["ids"]))[i]
            tm = (t["metadatas"] or [None] * len(t["ids"]))[j]

            document_changed = pd != td
            metadata_changed = pm != tm

            doc_diff += int(document_changed)
            metadata_diff += int(metadata_changed)

            pe = p["embeddings"]
            te = t["embeddings"]

            vector_changed = False
            cosine_distance_between_vectors = None
            max_abs_difference = None

            if pe is not None and te is not None:
                a = np.asarray(pe[i], dtype=np.float64)
                b = np.asarray(te[j], dtype=np.float64)

                vector_changed = not np.array_equal(a, b)

                if vector_changed:
                    embedding_diff += 1

                    if document_changed:
                        embedding_diff_changed_doc += 1
                    else:
                        embedding_diff_same_doc += 1

                norm_a = np.linalg.norm(a)
                norm_b = np.linalg.norm(b)

                if norm_a > 0 and norm_b > 0:
                    similarity = np.dot(a, b) / (norm_a * norm_b)
                    similarity = np.clip(similarity, -1.0, 1.0)
                    cosine_distance_between_vectors = 1.0 - similarity

                max_abs_difference = float(np.max(np.abs(a - b)))

            if (
                document_changed
                or metadata_changed
                or vector_changed
            ) and details_printed < max_details:
                details_printed += 1

                print(f"\n[{details_printed}] ID: {rid}")
                print(f"Document changed: {document_changed}")
                print(f"Metadata changed: {metadata_changed}")
                print(f"Embedding changed: {vector_changed}")

                if document_changed:
                    print(f"Production document: {str(pd)[:250]}")
                    print(f"Test document:       {str(td)[:250]}")

                if metadata_changed:
                    print(f"Production metadata: {str(pm)[:250]}")
                    print(f"Test metadata:       {str(tm)[:250]}")

                if vector_changed:
                    print(
                        "Cosine distance between stored vectors: "
                        f"{cosine_distance_between_vectors:.10f}"
                    )
                    print(
                        "Maximum absolute component difference: "
                        f"{max_abs_difference:.10f}"
                    )

    print("\n" + "=" * 75)
    print("FULL INTEGRITY SUMMARY")
    print("=" * 75)
    print(f"Production count: {total}")
    print(f"Test count: {test.count()}")
    print(f"Common IDs: {len(common_ids)}")
    print(f"IDs only in production: {len(only_prod)}")
    print(f"IDs only in test: {len(only_test)}")
    print(f"Different documents: {doc_diff}")
    print(f"Different metadata: {metadata_diff}")
    print(f"Different embeddings: {embedding_diff}")
    print(f"Embedding differs, document unchanged: {embedding_diff_same_doc}")
    print(f"Embedding differs, document changed: {embedding_diff_changed_doc}")
    print(f"Detailed records printed: {details_printed}")
    print("\nRead-only diagnostic. No collection was modified.")


def evaluate_retrieval_quality(collection, model, top_k=5):
    """
    Danh gia retrieval bang Recall@K, MRR@K va Hit@K.
    Chi doc collection, khong sua du lieu.

    Luu y: relevant_ids la nhan relevance ban dau,
    can duoc kiem tra lai bang danh gia thu cong.
    """
    test_cases = [
        {
            "topic": "Python",
            "query": "What is the difference between a list and a tuple in Python?",
            "relevant_ids": {
                "python_interview_question-0029",
            },
        },
        {
            "topic": "Java",
            "query": "Explain the difference between JDK, JRE, and JVM.",
            "relevant_ids": {
                "java_interview_question-0002",
                "java_interview_question-0001",
            },
        },
        {
            "topic": "React",
            "query": "What is the useEffect hook and when should it be used?",
            "relevant_ids": {
                "react_interview_question-0212",
                "react_interview_question-0283",
                "react_interview_question-0282",
                "react_interview_question-0285",
            },
        },
        {
            "topic": "SQL",
            "query": "Explain the difference between INNER JOIN and LEFT JOIN.",
            "relevant_ids": {
                "sql_interview_question-0018",
                "sql_interview_question-0007",
            },
        },
        {
            "topic": "Docker",
            "query": "What is the difference between a Docker image and a container?",
            "relevant_ids": {
                "docker_interview.question-0003",
                "docker_interview.question-0004",
            },
        },
        {
            "topic": "Git",
            "query": "What is the difference between git merge and git rebase?",
            "relevant_ids": {
                "git_interview_question-0023",
                "git_interview_question-0019",
            },
        },
        {
            "topic": "Spring",
            "query": "How does dependency injection work in Spring Boot?",
            "relevant_ids": {
                "spring_interview_question-0003",
                "spring_interview_question-0037",
                "spring_interview_question-0008",
                "spring_interview_question-0062",
            },
        },
        {
            "topic": "Machine Learning",
            "query": "Explain the difference between gradient descent and stochastic gradient descent.",
            "relevant_ids": {
                "ml_interview_question-0023",
            },
        },
    ]

    print("\n" + "=" * 75)
    print("RETRIEVAL QUALITY EVALUATION")
    print("=" * 75)
    print(f"Collection: {collection.name}")
    print(f"Top-K: {top_k}")
    print("Note: relevance labels are initial and require manual review.")

    results = []
    missing_relevant_ids = set()

    for case in test_cases:
        query = case["query"]
        relevant_ids = case["relevant_ids"]

        # Kiem tra nhung ID duoc gan nhan co ton tai trong collection.
        existing = collection.get(
            ids=list(relevant_ids),
            include=[],
        )
        existing_ids = set(existing["ids"])
        missing_relevant_ids.update(relevant_ids - existing_ids)

        if not existing_ids:
            print(f"\n[SKIP] {case['topic']}: no relevant IDs found.")
            continue

        query_embedding = model.encode(
            [query],
            normalize_embeddings=True,
        ).tolist()

        response = collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            include=["metadatas", "distances"],
        )

        ranked_ids = response["ids"][0]
        hits = [
            rank
            for rank, record_id in enumerate(ranked_ids, start=1)
            if record_id in existing_ids
        ]

        recall = len(set(ranked_ids) & existing_ids) / len(existing_ids)
        reciprocal_rank = 1.0 / hits[0] if hits else 0.0
        hit_at_k = 1.0 if hits else 0.0

        results.append({
            "topic": case["topic"],
            "recall": recall,
            "mrr": reciprocal_rank,
            "hit": hit_at_k,
        })

        print(f"\n--- {case['topic']} ---")
        print(f"Query: {query}")
        print(f"Relevant IDs: {len(existing_ids)}")
        print(f"Relevant IDs retrieved: {len(set(ranked_ids) & existing_ids)}")
        print(f"Recall@{top_k}: {recall:.4f}")
        print(f"MRR@{top_k}: {reciprocal_rank:.4f}")
        print(f"Hit@{top_k}: {int(hit_at_k)}")

        print("Ranked results:")
        for rank, record_id in enumerate(ranked_ids, start=1):
            marker = "RELEVANT" if record_id in existing_ids else ""
            print(f"  {rank}. {record_id} {marker}")

    print("\n" + "=" * 75)
    print("MACRO-AVERAGED METRICS")
    print("=" * 75)

    if results:
        count = len(results)
        avg_recall = sum(r["recall"] for r in results) / count
        avg_mrr = sum(r["mrr"] for r in results) / count
        avg_hit = sum(r["hit"] for r in results) / count

        print(f"Evaluated queries: {count}/{len(test_cases)}")
        print(f"Mean Recall@{top_k}: {avg_recall:.4f}")
        print(f"Mean MRR@{top_k}:    {avg_mrr:.4f}")
        print(f"Mean Hit@{top_k}:    {avg_hit:.4f}")

    if missing_relevant_ids:
        print("\nWARNING: These relevance-label IDs do not exist:")
        for record_id in sorted(missing_relevant_ids):
            print(f"  - {record_id}")

    print(
        "\nIMPORTANT: These scores are only as reliable as the relevance labels. "
        "Review the labels before using the scores to compare retrieval methods."
    )

    

# ==================== MAIN ====================

def main():
    print("=" * 75)
    print("RAG RETRIEVAL TEST")
    print("=" * 75)
    print(f"Production DB: {PRODUCTION_CHROMA_DIR}")
    print(f"Test DB: {TEST_CHROMA_DIR}")

    production_client = chromadb.PersistentClient(
        path=str(PRODUCTION_CHROMA_DIR)
    )
    test_client = chromadb.PersistentClient(
        path=str(TEST_CHROMA_DIR)
    )

    production_names = {
        item.name for item in production_client.list_collections()
    }
    test_names = {
        item.name for item in test_client.list_collections()
    }

    if PRODUCTION_COLLECTION not in production_names:
        raise RuntimeError(
            f"Production collection not found: {PRODUCTION_COLLECTION}"
        )

    if TEST_COLLECTION not in test_names:
        raise RuntimeError(
            f"Test collection not found: {TEST_COLLECTION}"
        )

    production = production_client.get_collection(
        PRODUCTION_COLLECTION
    )
    test = test_client.get_collection(TEST_COLLECTION)

    print(f"\nProduction count: {production.count()}")
    print(f"Final test count: {test.count()}")

    if production.count() == 0 or test.count() == 0:
        raise RuntimeError("A collection is empty.")

    # Kiem tra tat ca ban ghi, khong chi 20 ID dau tien.
    diagnose_all_records(production, test)

    print(f"\nLoading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    # Đánh giá chất lượng retrieval trên collection thử nghiệm
    evaluate_retrieval_quality(test, model, top_k=TOP_K)

    passed = 0

    for topic, query in TEST_QUERIES:
        print("\n" + "=" * 75)
        print(f"TOPIC: {topic}")
        print(f"QUERY: {query}")

        query_embedding = model.encode(
            query,
            normalize_embeddings=True,
            convert_to_numpy=True,
        ).tolist()

        results_by_collection = {}

        for label, collection in (
            ("PRODUCTION", production),
            ("FINAL TEST", test),
        ):
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(TOP_K, collection.count()),
                include=[
                    "documents",
                    "metadatas",
                    "distances",
                ],
            )

            ids = results["ids"][0]
            documents = results["documents"][0]
            metadatas = results["metadatas"][0]
            distances = results["distances"][0]

            results_by_collection[label] = ids

            print(f"\n--- {label} ---")

            for rank, (record_id, document, metadata, distance) in enumerate(
                zip(ids, documents, metadatas, distances),
                start=1,
            ):
                question = get_question(metadata, document)

                print(f"\n{rank}. ID: {record_id}")
                print(f"   Cosine distance: {distance:.4f}")
                print(f"   Content: {question[:350]}")

        production_top = set(results_by_collection["PRODUCTION"])
        test_top = set(results_by_collection["FINAL TEST"])

        print("\n--- TOP-K COMPARISON ---")
        print(f"Shared IDs: {len(production_top & test_top)}")
        print(f"Only in final test: {len(test_top - production_top)}")
        print(f"Only in production: {len(production_top - test_top)}")

        if production_top and test_top:
            passed += 1

    print("\n" + "=" * 75)
    print("FINAL SUMMARY")
    print("=" * 75)
    print(f"Queries returning results: {passed}/{len(TEST_QUERIES)}")
    print(f"Production records: {production.count()}")
    print(f"Final test records: {test.count()}")
    print("Read-only test completed.")
    print("No collection was modified.")


if __name__ == "__main__":
    main()
