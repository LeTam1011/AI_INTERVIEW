
from app.ai.question_retrieval import search_questions


def main():
    tests = [
        {
            "name": "Tìm kiếm OOP",
            "query": "Explain the four principles of OOP",
        },
        {
            "name": "Tìm kiếm SQL, lọc độ khó Medium",
            "query": "How do SQL joins work?",
            "category": "Database and SQL",
            "difficulty": "Medium",
        },
    ]

    for test in tests:
        print("\n" + "=" * 70)
        print(test["name"])

        results = search_questions(
            query=test["query"],
            top_k=5,
            category=test.get("category"),
            difficulty=test.get("difficulty"),
        )

        for index, item in enumerate(results, start=1):
            print(f"\n{index}. {item['question']}")
            print(f"   Category: {item['category']}")
            print(f"   Difficulty: {item['difficulty']}")
            print(f"   Similarity: {item['similarity']}")
            print(f"   Answer: {item['answer'][:200]}")


if __name__ == "__main__":
    main()
