from app.ai.question_retrieval import search_questions

results = search_questions(
    query="What are decorators in Python and how do they work?",
    top_k=3,
    topic="Python",
    answer_status="available",
    collection_name="python_questions_test_v1",
)

print("Results:", len(results))

for item in results:
    print("\nQuestion:", item["question"])
    print("Topic:", item["topic"])
    print("Similarity:", item["similarity"])
    print("Has answer:", bool(item["answer"]))